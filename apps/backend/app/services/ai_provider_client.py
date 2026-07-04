from typing import Optional

import httpx

from app.core.config import settings


class AIProviderError(Exception):
    """Raised when a configured provider call fails or isn't configured."""


class AIProviderClient:
    """Thin client that sends a grounded context + user question to a real
    LLM provider and returns its text reply. Each provider call includes the
    live telemetry context so the model answers from real data rather than
    training-time assumptions. If a provider isn't configured (missing API
    key, unreachable local Ollama) this raises AIProviderError so the caller
    can fall back to the deterministic rule-based assistant instead of
    silently fabricating an answer.
    """

    def __init__(self) -> None:
        self._timeout = settings.ai_request_timeout_seconds

    async def complete(self, provider: str, system_prompt: str, user_message: str) -> str:
        provider = (provider or settings.default_ai_provider).lower()

        try:
            if provider == "openai":
                return await self._complete_openai(system_prompt, user_message)
            if provider == "gemini":
                return await self._complete_gemini(system_prompt, user_message)
            if provider in ("claude", "anthropic"):
                return await self._complete_anthropic(system_prompt, user_message)
            if provider == "ollama":
                return await self._complete_ollama(system_prompt, user_message)
        except AIProviderError:
            raise
        except httpx.HTTPStatusError as error:
            detail = self._extract_error_detail(error)
            raise AIProviderError(
                f"{provider} request failed with HTTP {error.response.status_code}: {detail}"
            ) from error
        except httpx.RequestError as error:
            raise AIProviderError(f"Could not reach {provider}: {error}") from error
        except (KeyError, IndexError, ValueError) as error:
            raise AIProviderError(f"Unexpected response shape from {provider}: {error}") from error

        raise AIProviderError(f"Unknown AI provider '{provider}'.")

    def _extract_error_detail(self, error: httpx.HTTPStatusError) -> str:
        try:
            payload = error.response.json()
            return str(payload.get("error", payload))
        except Exception:
            return error.response.text[:200]

    async def _complete_openai(self, system_prompt: str, user_message: str) -> str:
        if not settings.openai_api_key:
            raise AIProviderError("OpenAI API key is not configured.")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    async def _complete_gemini(self, system_prompt: str, user_message: str) -> str:
        if not settings.gemini_api_key:
            raise AIProviderError("Gemini API key is not configured.")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url,
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_message}]}],
                    "generationConfig": {"temperature": 0.3},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    async def _complete_anthropic(self, system_prompt: str, user_message: str) -> str:
        if not settings.anthropic_api_key:
            raise AIProviderError("Anthropic API key is not configured.")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": settings.anthropic_model,
                    "max_tokens": 1000,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            response.raise_for_status()
            data = response.json()
            parts = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
            return "\n".join(parts).strip()

    async def _complete_ollama(self, system_prompt: str, user_message: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()