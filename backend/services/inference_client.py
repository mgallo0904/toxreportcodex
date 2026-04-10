"""Inference client for AI model interactions.

This module defines a lightweight wrapper around HTTP-based AI
inference services such as Ollama Cloud or Together AI.  All
other services should depend on this client rather than calling the
provider directly so that the backend can swap providers or adjust
request formats transparently.  The client uses httpx for
asynchronous HTTP requests.

Usage::

    settings = get_settings()
    model_tag = ...  # read active model tag from DB
    client = InferenceClient(settings.inference_base_url, settings.inference_api_key, model_tag)
    response_text = await client.complete(system_prompt, user_content, max_tokens=4000, temperature=0.0)

"""

from __future__ import annotations

from typing import Optional, Dict, Any

import httpx


class InferenceError(Exception):
    """Raised when the inference API returns an error or invalid response."""


class InferenceClient:
    """Client for performing text completions against a chat-based AI API.

    The client supports both Ollama Cloud and OpenAI-compatible APIs.  It
    automatically selects the appropriate endpoint based on the base URL
    provided at initialization.  Authentication is handled via bearer
    token if an API key is supplied.
    """

    def __init__(self, base_url: str, api_key: str, model_tag: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_tag = model_tag
        # Use a single httpx client instance for connection pooling
        self._client = httpx.AsyncClient(timeout=60.0)

    def _endpoint(self) -> str:
        """Determine the proper API endpoint based on the base URL.

        Ollama Cloud uses `/api/chat` whereas OpenAI-compatible services
        generally use `/v1/chat/completions`.  If the base_url contains
        'ollama', we assume the Ollama format; otherwise fall back to
        the OpenAI format.
        """
        lowered = self.base_url.lower()
        if 'ollama' in lowered:
            return f"{self.base_url}/api/chat"
        return f"{self.base_url}/v1/chat/completions"

    async def complete(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 4000,
        temperature: float = 0.0,
    ) -> str:
        """Request a completion from the underlying inference service.

        Parameters
        ----------
        system_prompt: str
            The system prompt providing context and instructions to the model.
        user_content: str
            The user message containing the content to process (e.g. chunk text).
        max_tokens: int, optional
            The maximum number of tokens to generate.  Defaults to 4000.
        temperature: float, optional
            Sampling temperature.  Defaults to 0.0 for deterministic output.

        Returns
        -------
        str
            The text content of the model's response.

        Raises
        ------
        InferenceError
            If the request fails or the response cannot be parsed.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        payload: Dict[str, Any] = {
            "model": self.model_tag,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = self._endpoint()
        try:
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover
            raise InferenceError(f"Inference request failed: {exc}") from exc
        data: Dict[str, Any]
        try:
            data = response.json()
        except Exception as exc:  # pragma: no cover
            raise InferenceError(f"Invalid JSON response: {exc}") from exc
        text: Optional[str] = None
        # Handle OpenAI-style and Ollama-style responses
        if isinstance(data, dict):
            # OpenAI: {"choices":[{"message":{"role":"assistant","content":"..."}}]}
            choices = data.get("choices")
            if choices and isinstance(choices, list) and choices:
                choice0 = choices[0]
                message = choice0.get("message") or {}
                text = message.get("content")
            else:
                # Ollama: {"message":{"role":"assistant","content":"..."}}
                message = data.get("message") or {}
                text = message.get("content")
        if not text:
            raise InferenceError("Inference API returned an unexpected response format.")
        return text
