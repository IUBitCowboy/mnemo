"""
Provider adapters for Mnemo CLI chat tool.

Each provider implements: chat(system_prompt: str, messages: list[dict]) -> str
where messages is the standard [{"role": "user"|"assistant", "content": "..."}] format.
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

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text


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

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
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
        return response.text


class OllamaProvider:
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, model: str):
        self.model = model
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def chat(self, system_prompt: str, messages: list[dict]) -> str:
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
        return response.json()["message"]["content"]
