#!/usr/bin/env python3
"""
Mnemo CLI Chat Tool

A local CLI for chatting with LLMs using persona files as system prompts.
Sessions are auto-saved as Markdown files.

FERPA note: This tool processes only instructor-written persona files and the
user's own prompts. It never reads, processes, or transmits student data.

Usage:
    python tools/chat.py --persona <path> [--provider anthropic|gemini|ollama]
                         [--model <name>] [--sessions-dir <dir>]
                         [--context <file> [<file> ...]]

Environment variables:
    ANTHROPIC_API_KEY   — required for Anthropic provider
    GEMINI_API_KEY      — required for Gemini provider
    OLLAMA_HOST         — Ollama server URL (default: http://localhost:11434)
    MNEMO_SESSIONS_DIR  — sessions output directory (default: ./sessions/)
"""

import argparse
import os
import sys
from pathlib import Path

# Allow running from any directory by adding tools/ to path
sys.path.insert(0, str(Path(__file__).parent))

from providers import get_provider, AnthropicProvider, GeminiProvider, OllamaProvider
from session import Session


PROVIDER_DEFAULTS = {
    "anthropic": AnthropicProvider.DEFAULT_MODEL,
    "gemini": GeminiProvider.DEFAULT_MODEL,
    "ollama": OllamaProvider.DEFAULT_MODEL,
}


def infer_provider(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gemini"):
        return "gemini"
    return "ollama"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mnemo CLI Chat — talk to an LLM using a persona file as system prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--persona", "-p",
        required=True,
        help="Path to persona/system prompt file (.md or .txt)",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "gemini", "ollama"],
        default=None,
        help="LLM provider (default: inferred from --model, or anthropic)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Model name (defaults: anthropic=claude-sonnet-4-6, gemini=gemini-3.0-flash-thinking, ollama=llama3.2)",
    )
    parser.add_argument(
        "--sessions-dir", "-s",
        default=None,
        help="Directory for session files (env: MNEMO_SESSIONS_DIR, default: ./sessions/)",
    )
    parser.add_argument(
        "--context", "-c",
        nargs="+",
        metavar="FILE",
        default=[],
        help="Knowledge base files to inject as a priming exchange before the conversation (e.g. clio_kb_SP26.md)",
    )
    return parser.parse_args()


def resolve_sessions_dir(cli_arg: str | None) -> str:
    if cli_arg:
        return cli_arg
    env_val = os.environ.get("MNEMO_SESSIONS_DIR")
    if env_val:
        return env_val
    return "./sessions/"


def resolve_provider_and_model(provider_arg: str | None, model_arg: str | None) -> tuple[str, str]:
    if model_arg and not provider_arg:
        provider = infer_provider(model_arg)
    elif not provider_arg:
        provider = "anthropic"
    else:
        provider = provider_arg

    model = model_arg if model_arg else PROVIDER_DEFAULTS[provider]
    return provider, model


def main():
    args = parse_args()

    # Resolve persona file
    persona_path = Path(args.persona)
    if not persona_path.exists():
        print(f"Error: persona file not found: {persona_path}", file=sys.stderr)
        sys.exit(1)
    system_prompt = persona_path.read_text(encoding="utf-8").strip()

    # Build priming messages from context files (injected as a synthetic
    # user/assistant exchange so the system prompt stays constant and cacheable)
    context_paths = []
    priming_messages = []
    for ctx in args.context:
        ctx_path = Path(ctx)
        if not ctx_path.exists():
            print(f"Error: context file not found: {ctx_path}", file=sys.stderr)
            sys.exit(1)
        content = ctx_path.read_text(encoding="utf-8").strip()
        priming_messages.append({
            "role": "user",
            "content": f"Here is the knowledge base for this session ({ctx_path.name}):\n\n{content}",
        })
        priming_messages.append({
            "role": "assistant",
            "content": "Understood. I have reviewed the knowledge base and am ready to assist.",
        })
        context_paths.append(ctx_path)

    # Resolve provider, model, sessions dir
    provider_name, model = resolve_provider_and_model(args.provider, args.model)
    sessions_dir = resolve_sessions_dir(args.sessions_dir)

    # Initialize provider (validates API keys etc.)
    try:
        provider = get_provider(provider_name, model)
    except (ImportError, EnvironmentError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize session recorder
    session = Session(
        sessions_dir=sessions_dir,
        persona_path=str(persona_path),
        provider=provider_name,
        model=model,
    )

    # Print header
    print(f"\n{'='*60}")
    print(f"  Mnemo CLI Chat")
    print(f"  Provider : {provider_name}")
    print(f"  Model    : {model}")
    print(f"  Persona  : {persona_path}")
    for ctx_path in context_paths:
        print(f"  Context  : {ctx_path}")
    print(f"  Sessions : {session.path}")
    print(f"{'='*60}")
    print("  Type your message and press Enter. 'quit' or Ctrl+D to exit.")
    print("  End a line with \\ to continue on the next line before sending.")
    print(f"{'='*60}\n")

    messages = priming_messages.copy()

    while True:
        # Read user input, supporting backslash line continuation
        try:
            user_input = input("You: ").strip()
            while user_input.endswith("\\"):
                user_input = user_input[:-1] + "\n" + input("... ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            break

        messages.append({"role": "user", "content": user_input})

        # Call provider
        try:
            response, usage = provider.chat(system_prompt, messages)
        except Exception as e:
            print(f"\nError from provider: {e}\n", file=sys.stderr)
            # Remove the failed user message so history stays consistent
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": response})

        # Print response
        print(f"\nAssistant: {response}\n")
        if usage:
            print(f"  [tokens — in: {usage['input_tokens']:,}  out: {usage['output_tokens']:,}  turn: {usage['input_tokens'] + usage['output_tokens']:,}]\n")

        # Append to session file immediately
        session.append_turn(user_input, response, usage)

    session.write_summary()

    if session._initialized:
        if session._total_input or session._total_output:
            total = session._total_input + session._total_output
            print(f"Session totals — in: {session._total_input:,}  out: {session._total_output:,}  total: {total:,} tokens")
        print(f"Session saved to: {session.path}")
    else:
        print("No messages exchanged — no session file created.")


if __name__ == "__main__":
    main()
