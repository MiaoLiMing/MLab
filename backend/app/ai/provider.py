from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class ProviderRequest:
    model: str
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderEvent:
    kind: str
    content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str | None = None


class ProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class OpenAICompatibleProvider:
    """Normalize an OpenAI-compatible chat completion stream."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def stream_chat(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": request.temperature,
            **request.extra,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    if response.status_code in {401, 403}:
                        raise ProviderError("MODEL_AUTH_FAILED", "模型 API Key 无效")
                    if response.status_code == 429:
                        raise ProviderError("MODEL_RATE_LIMITED", "模型服务请求过于频繁")
                    if response.status_code >= 400:
                        raise ProviderError("MODEL_REQUEST_FAILED", "模型服务返回异常")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        usage = chunk.get("usage") or {}
                        if usage:
                            yield ProviderEvent(
                                kind="usage",
                                input_tokens=int(usage.get("prompt_tokens") or 0),
                                output_tokens=int(usage.get("completion_tokens") or 0),
                            )
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        choice = choices[0]
                        delta = choice.get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield ProviderEvent(kind="delta", content=str(content))
                        if choice.get("finish_reason"):
                            yield ProviderEvent(
                                kind="finish", finish_reason=str(choice["finish_reason"])
                            )
        except ProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderError("MODEL_TIMEOUT", "模型响应超时") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("MODEL_UNAVAILABLE", "无法连接模型服务") from exc
