from collections.abc import AsyncIterator
from uuid import UUID

from httpx import AsyncClient

from app.ai.provider import MockChatProvider, ProviderEvent, ProviderRequest
from app.core.config import Settings
from app.db.session import SessionFactory
from app.models.entities import Assistant, Conversation, ToolDefinition, Visibility
from app.services.chat import ResolvedModel, resolve_model


async def test_stream_chat_with_attachment(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    upload = await client.post(
        "/api/v1/files",
        headers=auth_headers,
        files={"upload": ("notes.txt", b"project constraint: use sqlite locally", "text/plain")},
    )
    assert upload.status_code == 201

    assistant = await client.post(
        "/api/v1/assistants",
        headers=auth_headers,
        json={
            "name": "项目助手",
            "system_prompt": "只回答项目问题",
            "opening_message": "请上传项目资料。",
            "model_config": {"temperature": 0.3, "max_tokens": 512},
            "knowledge_file_ids": [upload.json()["id"]],
        },
    )
    assert assistant.status_code == 201
    assert assistant.json()["opening_message"] == "请上传项目资料。"
    assert assistant.json()["knowledge_file_ids"] == [upload.json()["id"]]
    memory = await client.post(
        "/api/v1/memories",
        headers=auth_headers,
        json={"content": "MEMORY_SHOULD_NOT_BE_USED", "category": "preference"},
    )
    assert memory.status_code == 201
    profile = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={
            "default_assistant_id": assistant.json()["id"],
            "memory_enabled": False,
        },
    )
    assert profile.status_code == 200
    conversation = await client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "新对话"},
    )
    assert conversation.json()["assistant_id"] == assistant.json()["id"]

    async def fake_resolve_model(*_args, **_kwargs) -> ResolvedModel:
        return ResolvedModel(
            provider="fake",
            model="fake-model",
            base_url="https://example.invalid/v1",
            api_key="test-key",
            temperature=0.2,
            max_tokens=100,
        )

    async def fake_stream(_self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        assert any("project constraint" in item["content"] for item in request.messages)
        assert all("MEMORY_SHOULD_NOT_BE_USED" not in item["content"] for item in request.messages)
        yield ProviderEvent(kind="delta", content="已读取附件")
        yield ProviderEvent(kind="usage", input_tokens=10, output_tokens=4)

    monkeypatch.setattr("app.api.v1.conversations.resolve_model", fake_resolve_model)
    monkeypatch.setattr("app.ai.provider.OpenAICompatibleProvider.stream_chat", fake_stream)
    response = await client.post(
        f"/api/v1/conversations/{conversation.json()['id']}/messages",
        headers=auth_headers,
        json={"content": "总结附件", "attachment_ids": [upload.json()["id"]]},
    )
    assert response.status_code == 200
    assert "message.delta" in response.text
    assert "已读取附件" in response.text

    detail = await client.get(
        f"/api/v1/conversations/{conversation.json()['id']}", headers=auth_headers
    )
    assert len(detail.json()["messages"]) == 2
    assert len(detail.json()["messages"][0]["attachments"]) == 1
    assert detail.json()["messages"][0]["attachments"][0]["attachment_metadata"] == {
        "name": "notes.txt",
        "mime_type": "text/plain",
    }
    assert detail.json()["messages"][1]["content"] == "已读取附件"

    source_message_id = detail.json()["messages"][0]["id"]
    regenerated = await client.post(
        f"/api/v1/conversations/{conversation.json()['id']}/messages",
        headers=auth_headers,
        json={"content": "重新总结附件", "source_message_id": source_message_id},
    )
    assert regenerated.status_code == 200
    refreshed = await client.get(
        f"/api/v1/conversations/{conversation.json()['id']}", headers=auth_headers
    )
    assert len(refreshed.json()["messages"]) == 2
    assert refreshed.json()["messages"][0]["content"] == "重新总结附件"
    assert len(refreshed.json()["messages"][0]["attachments"]) == 1

    updated_assistant = await client.patch(
        f"/api/v1/assistants/{assistant.json()['id']}",
        headers=auth_headers,
        json={"opening_message": "从目标开始。"},
    )
    assert updated_assistant.status_code == 200
    assert updated_assistant.json()["opening_message"] == "从目标开始。"


async def test_builtin_tool_execution_and_expression_safety(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    async with SessionFactory() as db:
        tool = ToolDefinition(
            name="安全计算器",
            slug="calculator",
            description="计算",
            icon="Calculator",
            category="效率",
            access_type="openai_tool",
            external_url=None,
            rating=5,
            config_schema={},
        )
        db.add(tool)
        await db.commit()
        await db.refresh(tool)
        tool_id = tool.id

    result = await client.post(
        f"/api/v1/tools/{tool_id}/execute",
        headers=auth_headers,
        json={"input": {"expression": "(12 + 8) * 3"}},
    )
    assert result.status_code == 200
    assert result.json()["output"]["result"] == 60

    unsafe = await client.post(
        f"/api/v1/tools/{tool_id}/execute",
        headers=auth_headers,
        json={"input": {"expression": "__import__('os').system('whoami')"}},
    )
    assert unsafe.status_code == 422
    assert unsafe.json()["error"]["code"] == "INVALID_EXPRESSION"


async def test_chat_model_tool_call_round_trip(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    async with SessionFactory() as db:
        tool = ToolDefinition(
            name="安全计算器",
            slug="calculator",
            description="计算",
            icon="Calculator",
            category="效率",
            access_type="openai_tool",
            external_url=None,
            rating=5,
            config_schema={},
        )
        db.add(tool)
        await db.commit()

    conversation = await client.post(
        "/api/v1/conversations", headers=auth_headers, json={"title": "计算"}
    )

    async def fake_resolve_model(*_args, **_kwargs) -> ResolvedModel:
        return ResolvedModel(
            provider="fake",
            model="fake-model",
            base_url="https://example.invalid/v1",
            api_key="test-key",
            temperature=0.2,
            max_tokens=100,
        )

    calls = 0

    async def fake_stream(_self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        nonlocal calls
        calls += 1
        if calls == 1:
            assert request.tools
            yield ProviderEvent(
                kind="tool_delta",
                tool_index=0,
                tool_call_id="call-1",
                tool_name="calculator",
                tool_arguments='{"expression":"6 * 7"}',
            )
            yield ProviderEvent(kind="finish", finish_reason="tool_calls")
        else:
            assert any(message.get("role") == "tool" for message in request.messages)
            yield ProviderEvent(kind="delta", content="结果是 42。")

    monkeypatch.setattr("app.api.v1.conversations.resolve_model", fake_resolve_model)
    monkeypatch.setattr("app.ai.provider.OpenAICompatibleProvider.stream_chat", fake_stream)
    response = await client.post(
        f"/api/v1/conversations/{conversation.json()['id']}/messages",
        headers=auth_headers,
        json={"content": "请计算 6 * 7"},
    )
    assert response.status_code == 200
    assert "tool.call" in response.text
    assert "tool.result" in response.text
    assert "结果是 42" in response.text
    assert calls == 2


async def test_document_ai_versions_and_task_breakdown(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    async def fake_complete(*_args, **_kwargs) -> str:
        return "- 第一步\n- 第二步"

    monkeypatch.setattr("app.api.v1.documents.complete_text", fake_complete)
    monkeypatch.setattr("app.api.v1.tasks.complete_text", fake_complete)

    document = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={"title": "原稿", "content_json": {}, "content_text": "待改写内容"},
    )
    action = await client.post(
        f"/api/v1/documents/{document.json()['id']}/ai-actions",
        headers=auth_headers,
        json={"action": "rewrite"},
    )
    assert action.status_code == 200
    assert "第一步" in action.json()["content"]

    updated = await client.patch(
        f"/api/v1/documents/{document.json()['id']}",
        headers=auth_headers,
        json={
            "content_text": "第二版",
            "content_json": {"type": "doc"},
            "create_version": True,
        },
    )
    versions = await client.get(
        f"/api/v1/documents/{document.json()['id']}/versions", headers=auth_headers
    )
    assert updated.json()["current_version"] == 2
    assert len(versions.json()) == 2
    restored = await client.post(
        f"/api/v1/documents/{document.json()['id']}/versions/1/restore",
        headers=auth_headers,
    )
    assert restored.json()["content_text"] == "待改写内容"
    assert restored.json()["current_version"] == 3

    task = await client.post("/api/v1/tasks", headers=auth_headers, json={"title": "发布产品"})
    breakdown = await client.post(
        f"/api/v1/tasks/{task.json()['id']}/ai-breakdown",
        headers=auth_headers,
        json={},
    )
    assert breakdown.status_code == 200
    tasks = await client.get("/api/v1/tasks", headers=auth_headers)
    assert tasks.json()[0]["content"] == "- 第一步\n- 第二步"


async def test_assistant_model_parameters_override_system_defaults(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    profile = await client.get("/api/v1/users/me", headers=auth_headers)
    user_id = UUID(profile.json()["id"])
    async with SessionFactory() as db:
        assistant = Assistant(
            owner_id=user_id,
            name="参数助手",
            slug="parameter-assistant",
            description="",
            avatar="参",
            system_prompt="",
            opening_message="",
            category="测试",
            visibility=Visibility.PRIVATE,
            model_config={"temperature": 1.2, "max_tokens": 321},
        )
        db.add(assistant)
        await db.flush()
        conversation = Conversation(user_id=user_id, assistant_id=assistant.id, title="参数测试")
        db.add(conversation)
        await db.commit()
        resolved = await resolve_model(
            db,
            Settings(ai_api_key="system-test-key"),
            assistant.owner_id,
            None,
            conversation,
        )
    assert resolved.temperature == 1.2
    assert resolved.max_tokens == 321


async def test_mock_provider_streams_and_requests_builtin_tools() -> None:
    provider = MockChatProvider()
    events = [
        event
        async for event in provider.stream_chat(
            ProviderRequest(
                model="mlab-mock",
                messages=[{"role": "user", "content": "请计算 6 * 7"}],
                tools=[
                    {
                        "type": "function",
                        "function": {"name": "calculator", "parameters": {}},
                    }
                ],
            )
        )
    ]
    assert events[0].kind == "tool_delta"
    assert events[0].tool_name == "calculator"
    assert "6 * 7" in events[0].tool_arguments

    streamed = [
        event
        async for event in provider.stream_chat(
            ProviderRequest(
                model="mlab-mock",
                messages=[{"role": "user", "content": "给我一段 Python 代码"}],
            )
        )
    ]
    assert "```python" in "".join(event.content for event in streamed)
    assert streamed[-1].kind == "usage"
