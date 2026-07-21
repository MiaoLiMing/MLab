from collections.abc import AsyncIterator

from httpx import AsyncClient

from app.ai.provider import ProviderEvent, ProviderRequest
from app.db.session import SessionFactory
from app.models.entities import ToolDefinition
from app.services.chat import ResolvedModel


async def test_stream_chat_with_attachment(
    client: AsyncClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    upload = await client.post(
        "/api/v1/files",
        headers=auth_headers,
        files={"upload": ("notes.txt", b"project constraint: use sqlite locally", "text/plain")},
    )
    assert upload.status_code == 201

    conversation = await client.post(
        "/api/v1/conversations", headers=auth_headers, json={"title": "新对话"}
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

    async def fake_stream(_self, request: ProviderRequest) -> AsyncIterator[ProviderEvent]:
        assert "project constraint" in request.messages[-1]["content"]
        yield ProviderEvent(kind="delta", content="已读取附件")
        yield ProviderEvent(kind="usage", input_tokens=10, output_tokens=4)

    monkeypatch.setattr("app.api.v1.conversations.resolve_model", fake_resolve_model)
    monkeypatch.setattr(
        "app.api.v1.conversations.OpenAICompatibleProvider.stream_chat", fake_stream
    )
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
    assert detail.json()["messages"][1]["content"] == "已读取附件"


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
        json={"content_text": "第二版", "content_json": {"type": "doc"}},
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
