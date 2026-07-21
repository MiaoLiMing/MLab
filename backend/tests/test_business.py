from httpx import AsyncClient


async def test_tasks_documents_resources_and_memories(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    task = await client.post(
        "/api/v1/tasks", headers=auth_headers, json={"title": "完成验收", "priority": "high"}
    )
    assert task.status_code == 201
    completed = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}", headers=auth_headers, json={"status": "done"}
    )
    assert completed.json()["completed_at"] is not None

    document = await client.post(
        "/api/v1/documents",
        headers=auth_headers,
        json={"title": "方案", "content_json": {}, "content_text": "第一版"},
    )
    updated = await client.patch(
        f"/api/v1/documents/{document.json()['id']}",
        headers=auth_headers,
        json={"content_text": "第二版", "content_json": {"type": "doc"}},
    )
    assert updated.json()["current_version"] == 2

    resource = await client.post(
        "/api/v1/resources",
        headers=auth_headers,
        json={"resource_type": "prompt", "title": "测试提示词", "content": "内容"},
    )
    assert resource.status_code == 201

    memory = await client.post(
        "/api/v1/memories",
        headers=auth_headers,
        json={"content": "偏好简短回答", "category": "preference"},
    )
    toggled = await client.patch(
        f"/api/v1/memories/{memory.json()['id']}", headers=auth_headers, json={"enabled": False}
    )
    assert toggled.json()["enabled"] is False


async def test_user_data_is_isolated(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    task = await client.post(
        "/api/v1/tasks", headers=auth_headers, json={"title": "私有任务", "priority": "normal"}
    )
    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "password123", "display_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    response = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}", headers=other_headers, json={"status": "done"}
    )
    assert response.status_code == 404
