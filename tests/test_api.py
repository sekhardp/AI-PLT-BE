import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    """Test health check endpoints."""
    # Test root health
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    # Test api health
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_chat_and_history_flow(client: AsyncClient):
    """Test chat posting and verification in history."""
    # 1. Post a chat message
    chat_payload = {"prompt": "What is the capital of France?", "session_id": "test-session-123"}
    resp = await client.post("/api/v1/chat", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-session-123"
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert "France" in data["message"]["content"]

    # 2. Get history for session
    resp = await client.get("/api/v1/history/test-session-123")
    assert resp.status_code == 200
    history_data = resp.json()
    assert history_data["session_id"] == "test-session-123"
    assert len(history_data["messages"]) == 2
    assert history_data["messages"][0]["role"] == "user"
    assert history_data["messages"][0]["content"] == "What is the capital of France?"
    assert history_data["messages"][1]["role"] == "assistant"

    # 3. List all sessions
    resp = await client.get("/api/v1/history")
    assert resp.status_code == 200
    sessions_data = resp.json()
    assert len(sessions_data["sessions"]) >= 1
    assert any(s["session_id"] == "test-session-123" for s in sessions_data["sessions"])


@pytest.mark.asyncio
async def test_feedback_flow(client: AsyncClient):
    """Test logging and listing user feedback."""
    feedback_payload = {
        "session_id": "test-session-123",
        "message_id": "msg-456",
        "rating": 5,
        "comment": "Outstanding response!"
    }
    # 1. Post feedback
    resp = await client.post("/api/v1/feedback", json=feedback_payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "received"
    feedback_id = res_data["feedback_id"]

    # 2. List feedback
    resp = await client.get("/api/v1/feedback")
    assert resp.status_code == 200
    all_feedback = resp.json()["feedback"]
    assert len(all_feedback) >= 1
    match = next((f for f in all_feedback if f["feedback_id"] == feedback_id), None)
    assert match is not None
    assert match["rating"] == 5
    assert match["comment"] == "Outstanding response!"


@pytest.mark.asyncio
async def test_upload_endpoint(client: AsyncClient):
    """Test file upload validation and storage."""
    files = {"file": ("test.txt", b"Hello, this is a test file content.", "text/plain")}
    resp = await client.post("/api/v1/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "file_id" in data
    assert data["filename"] == "test.txt"
    assert data["size_bytes"] == len(b"Hello, this is a test file content.")
    assert data["content_type"] == "text/plain"
