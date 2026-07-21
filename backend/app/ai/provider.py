from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class ProviderRequest:
    model: str
    messages: list[dict[str, Any]]
    temperature: float = 0.7
    max_tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ProviderEvent:
    kind: str
    content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str | None = None
    tool_index: int = 0
    tool_call_id: str = ""
    tool_name: str = ""
    tool_arguments: str = ""


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
        if request.tools:
            payload["tools"] = request.tools
            payload["tool_choice"] = "auto"

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
                        for tool_call in delta.get("tool_calls") or []:
                            function = tool_call.get("function") or {}
                            yield ProviderEvent(
                                kind="tool_delta",
                                tool_index=int(tool_call.get("index") or 0),
                                tool_call_id=str(tool_call.get("id") or ""),
                                tool_name=str(function.get("name") or ""),
                                tool_arguments=str(function.get("arguments") or ""),
                            )
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


class MockChatProvider:
    """Deterministic development provider that exercises the real SSE and tool pipeline."""

    async def stream_chat(self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        latest_user = next(
            (
                str(message.get("content") or "")
                for message in reversed(request.messages)
                if message.get("role") == "user"
            ),
            "",
        )
        tool_message = next(
            (
                str(message.get("content") or "")
                for message in reversed(request.messages)
                if message.get("role") == "tool"
            ),
            "",
        )
        if request.tools and not tool_message:
            tool = self._select_tool(request.tools, latest_user)
            if tool:
                name, arguments = tool
                yield ProviderEvent(
                    kind="tool_delta",
                    tool_call_id="mock-tool-call",
                    tool_name=name,
                    tool_arguments=json.dumps(arguments, ensure_ascii=False),
                )
                yield ProviderEvent(kind="finish", finish_reason="tool_calls")
                return

        response = self._response(request, latest_user, tool_message)
        for offset in range(0, len(response), 12):
            await asyncio.sleep(0.015)
            yield ProviderEvent(kind="delta", content=response[offset : offset + 12])
        yield ProviderEvent(
            kind="usage",
            input_tokens=max(
                1, sum(len(str(item.get("content") or "")) for item in request.messages) // 4
            ),
            output_tokens=max(1, len(response) // 4),
        )

    @staticmethod
    def _select_tool(
        tools: list[dict[str, Any]], user_content: str
    ) -> tuple[str, dict[str, str]] | None:
        names = {str((tool.get("function") or {}).get("name") or "") for tool in tools}
        normalized = user_content.lower()
        if "calculator" in names and any(
            word in normalized for word in ("计算", "算一下", "等于", "calculate", "calculator")
        ):
            match = re.search(r"[\d\s()+\-*/%.]{3,}", user_content)
            return "calculator", {"expression": (match.group(0).strip() if match else "6 * 7")}
        if "current-time" in names and any(
            word in normalized for word in ("时间", "几点", "日期", "time", "date")
        ):
            zone = "Asia/Shanghai"
            zone_match = re.search(r"[A-Za-z]+/[A-Za-z_]+", user_content)
            if zone_match:
                zone = zone_match.group(0)
            return "current-time", {"timezone": zone}
        return None

    @staticmethod
    def _response(request: ProviderRequest, user_content: str, tool_message: str) -> str:
        system_content = "\n".join(
            str(message.get("content") or "")
            for message in request.messages
            if message.get("role") == "system"
        )
        if tool_message:
            return f"工具已经完成调用，结果如下：\n\n```json\n{tool_message}\n```"
        if "执行计划助手" in system_content:
            return (
                "- [ ] 明确目标与验收标准\n"
                "- [ ] 拆分核心步骤并确认依赖\n"
                "- [ ] 执行后记录结果与风险\n"
                "- [ ] 按验收标准完成复核"
            )
        if "中文写作助手" in system_content:
            if "提炼核心观点" in user_content:
                return (
                    "## 核心摘要\n\n"
                    "- 保留原文主要事实与结论\n"
                    "- 明确下一步行动项\n"
                    "- 需要人工复核关键数据"
                )
            if "延续原文" in user_content:
                return "在此基础上，下一步应明确责任人、时间节点与验收方式，并持续记录执行结果。"
            return "这是经过结构优化的版本：表达更直接，重点更清晰，并保留了原文中的事实边界。"
        if any(word in user_content.lower() for word in ("代码", "code", "python")):
            return (
                "下面是一个可直接运行的示例：\n\n"
                "```python\n"
                "def hello(name: str) -> str:\n"
                '    return f"Hello, {name}"\n'
                "```"
            )
        return (
            "这是 Mock 模型返回的流式回复。\n\n"
            f"你刚才提出的是：**{user_content or '开始一段新对话'}**。\n\n"
            "认证、数据库持久化、SSE 解析、停止生成和历史恢复仍使用真实系统链路。"
        )


def create_provider(
    provider: str, base_url: str, api_key: str, *, timeout: float = 120
) -> OpenAICompatibleProvider | MockChatProvider:
    if provider == "mock":
        return MockChatProvider()
    return OpenAICompatibleProvider(base_url, api_key, timeout=timeout)
