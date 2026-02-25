"""
Provider adapters for Mnemo CLI chat tool.

Each provider implements: chat(system_prompt: str, messages: list[dict]) -> (str, dict)
where the tuple is (response_text, usage) and usage is:
  {"input_tokens": int, "output_tokens": int}
or None if the provider does not report usage.
"""

import os
import json
import requests


def get_provider(name: str, model: str):
    providers = {
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
    }
    if name not in providers:
        raise ValueError(f"Unknown provider '{name}'. Choose from: {', '.join(providers)}")
    return providers[name](model)


class AnthropicProvider:
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, model: str):
        try:
            import anthropic as anthropic_sdk
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic_sdk.Anthropic(api_key=api_key)
        self.model = model

    def chat(self, system_prompt: str, messages: list[dict]) -> tuple:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return response.content[0].text, usage


class GeminiProvider:
    DEFAULT_MODEL = "gemini-3.0-flash-thinking"

    def __init__(self, model: str):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        self.genai = genai
        self.model = model

    def chat(self, system_prompt: str, messages: list[dict]) -> tuple:
        model = self.genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt,
        )
        # Convert messages to Gemini format
        history = []
        for msg in messages[:-1]:  # All but last message go into history
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history)
        response = chat.send_message(messages[-1]["content"])
        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
            }
        return response.text, usage


class OllamaProvider:
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, model: str):
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def chat(self, system_prompt: str, messages: list[dict]) -> tuple:
        # Prepend system prompt as a system message
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": False,
        }
        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
        except requests.ConnectionError:
            raise ConnectionError(f"Cannot connect to Ollama at {self.host}. Is Ollama running?")
        data = response.json()
        usage = None
        if "prompt_eval_count" in data and "eval_count" in data:
            usage = {
                "input_tokens": data["prompt_eval_count"],
                "output_tokens": data["eval_count"],
            }
        return data["message"]["content"], usage
