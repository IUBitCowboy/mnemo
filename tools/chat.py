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
import threading
import time
from pathlib import Path

try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.formatted_text import HTML
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

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


def _cache_toolbar(last_response_time: float, cache_ttl: int):
    """Return a prompt_toolkit HTML toolbar string showing cache countdown."""
    remaining = cache_ttl - (time.time() - last_response_time)
    if remaining <= 0:
        return HTML('<style bg="ansired" fg="ansiwhite"> cache: EXPIRED </style>')
    elif remaining <= 10:
        label = f"cache: {int(remaining)}s"
        return HTML(f'<style bg="ansired" fg="ansiwhite"> {label} </style>')
    elif remaining <= 60:
        # Round to nearest 5 so the display only visually steps every ~5 seconds
        rounded = round(remaining / 5) * 5
        label = f"cache: {rounded}s"
        return HTML(f'<style bg="ansiyellow" fg="ansiblack"> {label} </style>')
    else:
        # Display in whole minutes — changes once per minute
        label = f"cache: {int(remaining // 60)}m"
        return HTML(f'<style bg="ansigreen" fg="ansiwhite"> {label} </style>')


def _waiting_indicator(stop_event: threading.Event, start_time: float) -> None:
    """Background thread: print a running elapsed timer while waiting for API response."""
    while not stop_event.is_set():
        elapsed = time.time() - start_time
        if elapsed < 60:
            label = f"  ⏳ Submitted — waiting... {elapsed:.1f}s"
        else:
            m = int(elapsed // 60)
            s = elapsed % 60
            label = f"  ⏳ Submitted — waiting... {m}m {s:.0f}s"
        sys.stdout.write(f"\r{label}   ")
        sys.stdout.flush()
        time.sleep(0.1)
    # Clear the indicator line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


def read_input(last_response_time: float | None, cache_ttl: int) -> str:
    """Read a line of user input, with live cache countdown toolbar when available."""
    if HAS_PROMPT_TOOLKIT and last_response_time is not None:
        def toolbar():
            return _cache_toolbar(last_response_time, cache_ttl)
        line = pt_prompt("You: ", bottom_toolbar=toolbar, refresh_interval=1.0).strip()
        while line.endswith("\\"):
            line = line[:-1] + "\n" + pt_prompt("... ").strip()
    else:
        line = input("You: ").strip()
        while line.endswith("\\"):
            line = line[:-1] + "\n" + input("... ").strip()
    return line


def mark_priming_for_cache(messages: list[dict]) -> list[dict]:
    """Return a copy of messages with the last entry's content marked for caching.

    Converts the last message's string content to the Anthropic list format
    with cache_control so the entire system+priming prefix is cached as one block.
    """
    if not messages:
        return messages
    result = [dict(m) for m in messages]
    last = result[-1]
    if isinstance(last["content"], str):
        last["content"] = [
            {"type": "text", "text": last["content"], "cache_control": {"type": "ephemeral"}}
        ]
    return result


def format_usage(usage: dict) -> str:
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    hit = usage.get("cache_read", 0)
    write = usage.get("cache_write", 0)

    parts = [f"in: {inp:,}"]
    if hit:
        parts.append(f"cached: {hit:,}")
    if write:
        parts.append(f"cache_write: {write:,}")
    parts.append(f"out: {out:,}")
    parts.append(f"turn: {inp + out:,}")
    return "  ".join(parts)


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
        context_files=[str(p) for p in context_paths] or None,
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
    print("  /new  — save this session and start a fresh one  (// to send a literal /)")
    print(f"{'='*60}\n")

    # Mark last priming message for caching if the provider supports it
    if priming_messages and hasattr(provider, "supports_caching") and provider.supports_caching():
        priming_messages = mark_priming_for_cache(priming_messages)

    cache_ttl = getattr(provider, "CACHE_TTL", 300)
    messages = priming_messages.copy()
    last_response_time: float | None = None

    while True:
        # Read user input with live cache countdown (if prompt_toolkit available)
        try:
            user_input = read_input(last_response_time, cache_ttl)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            break

        # Slash commands — // escapes to a literal /
        if user_input.startswith("/"):
            if user_input.startswith("//"):
                user_input = user_input[1:]  # strip one slash, send the rest
            elif user_input.lower() == "/new":
                # Finalise current session and open a fresh one
                session.write_summary()
                if session._initialized:
                    print(f"  Session saved: {session.path}\n")
                session = Session(
                    sessions_dir=sessions_dir,
                    persona_path=str(persona_path),
                    provider=provider_name,
                    model=model,
                )
                messages = priming_messages.copy()
                last_response_time = None
                print(f"  New session — {session.path}\n")
                continue
            else:
                print(f"  Unknown command '{user_input}'. Known: /new  (use // for a literal /)\n")
                continue

        messages.append({"role": "user", "content": user_input})

        # Capture timing: gap since last response, then measure API call duration
        prompt_at = time.time()
        since_last = (prompt_at - last_response_time) if last_response_time is not None else None

        # Start elapsed-time indicator while waiting for API response
        stop_waiting = threading.Event()
        waiting_thread = threading.Thread(
            target=_waiting_indicator, args=(stop_waiting, prompt_at), daemon=True
        )
        waiting_thread.start()

        # Call provider
        try:
            response, usage = provider.chat(system_prompt, messages)
            response_at = time.time()
            last_response_time = response_at
        except Exception as e:
            stop_waiting.set()
            waiting_thread.join()
            print(f"\nError from provider: {e}\n", file=sys.stderr)
            # Remove the failed user message so history stays consistent
            messages.pop()
            continue

        stop_waiting.set()
        waiting_thread.join()

        timing = {
            "response_s": response_at - prompt_at,
            "since_last_s": since_last,
        }

        messages.append({"role": "assistant", "content": response})

        # Print response
        print(f"\nAssistant: {response}\n")
        if usage:
            print(f"  [{format_usage(usage)}]\n")

        # Append to session file immediately
        session.append_turn(user_input, response, usage, timing)

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
