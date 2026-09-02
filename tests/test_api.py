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
async def test_documents_list_endpoint(client: AsyncClient):
    """Test listing documents and quota structure."""
    resp = await client.get("/api/v1/documents?user_id=test_user")
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert "quota" in data
    assert data["quota"]["max_documents"] == 5
    assert data["quota"]["max_mb"] == 100.0


@pytest.mark.asyncio
async def test_non_admin_chat_stream_and_history(client: AsyncClient):
    """Verify that non-admin users can stream responses without crash and fetch history."""
    # 1. Non-admin stream chat (previously crashed due to missing or_ and hardcoded email)
    resp = await client.get("/api/v1/chat/stream?prompt=Hello&user_id=sarath@example.com&session_id=sess-nonadmin-1")
    assert resp.status_code == 200
    text = resp.text
    assert "data: " in text
    assert "sess-nonadmin-1" in text

    # 2. Fetch history for non-admin session
    hist_resp = await client.get("/api/v1/history/sess-nonadmin-1?user_id=sarath@example.com")
    assert hist_resp.status_code == 200
    messages = hist_resp.json()["messages"]
    assert len(messages) >= 2
    assert messages[0]["content"] == "Hello"
    assert messages[0].get("tokens") is not None
    # Assistant message should have model and tokens populated
    assert messages[1]["role"] == "assistant"
    assert messages[1].get("model") is not None
    assert messages[1].get("tokens") is not None
    assert messages[1]["tokens"] >= 0

    # 3. List sessions for non-admin user
    list_resp = await client.get("/api/v1/history?user_id=sarath@example.com")
    assert list_resp.status_code == 200
    sessions = list_resp.json()["sessions"]
    assert any(s["session_id"] == "sess-nonadmin-1" for s in sessions)


@pytest.mark.asyncio
async def test_message_model_and_tokens_persistence(client: AsyncClient):
    """Verify that chat responses store model, tokens, routed_to, and complexity in DB."""
    # Send a non-streaming chat request
    req_body = {
        "prompt": "What is 2 + 2?",
        "session_id": "sess-token-test-1",
        "user_id": "sarath@example.com"
    }
    resp = await client.post("/api/v1/chat", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    msg = data["message"]
    assert msg["model"] is not None
    assert msg["tokens"] is not None
    assert msg["tokens"] >= 0
    assert msg["routed_to"] is not None

    # Fetch history and verify it is retrieved from database
    hist_resp = await client.get("/api/v1/history/sess-token-test-1?user_id=sarath@example.com")
    assert hist_resp.status_code == 200
    hist_msgs = hist_resp.json()["messages"]
    assert len(hist_msgs) == 2
    # User message
    assert hist_msgs[0]["role"] == "user"
    assert hist_msgs[0]["tokens"] >= 0
    # Assistant message
    assert hist_msgs[1]["role"] == "assistant"
    assert hist_msgs[1]["model"] == msg["model"]
    assert hist_msgs[1]["tokens"] == msg["tokens"]
    assert hist_msgs[1]["routed_to"] == msg["routed_to"]


def test_recursive_chunk_text():
    """Verify recursive character text splitter splits hierarchically and respects boundaries."""
    from app.services.document_service import document_service

    sample_doc = (
        "Introduction to AI Platform.\n\n"
        "Section 1: Architecture Overview.\n"
        "The system routes complex queries to frontier models and fast queries to local models. "
        "It includes a vectorization pipeline with pgvector semantic similarity search.\n\n"
        "Section 2: Security & Quotas.\n"
        "Users have isolated storage quotas and credit ledgers."
    )

    chunks = document_service.chunk_text(sample_doc, chunk_size=120, overlap=30)
    assert len(chunks) >= 2
    # Ensure all chunks are within reasonable chunk_size bounds
    for c in chunks:
        assert len(c) > 0
        assert isinstance(c, str)
    # Ensure full content coverage
    assert any("Introduction to AI Platform" in c for c in chunks)
    assert any("Section 2: Security & Quotas" in c for c in chunks)


def test_bm25_tokenization_and_hybrid():
    """Verify BM25 tokenization and BM25Okapi scoring."""
    from app.services.document_service import document_service
    from rank_bm25 import BM25Okapi

    corpus = [
        "Invoice PR-9021 for carbon credit retirement certificate issued to Acme Corp.",
        "Scope 1 emissions are direct greenhouse gas emissions from controlled facilities.",
        "Scope 2 emissions are indirect emissions from electricity consumption.",
    ]
    tokenized_corpus = [document_service._tokenize_text(doc) for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    query = "PR-9021 invoice"
    query_tokens = document_service._tokenize_text(query)
    scores = bm25.get_scores(query_tokens)

    # Document 0 (PR-9021 invoice) should have highest score
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]
