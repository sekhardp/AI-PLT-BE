import json
import logging
import uuid
from datetime import datetime, UTC
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.clients.agent_client import AgentClientError
from app.db.rag_session import get_rag_db
from app.services.agent_service import AgentService, get_agent_service
from app.services.chat_service import ChatService, get_chat_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.rag_service import rag_service
from app.services.user_service import user_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Execute a chat prompt and store messages with exact model token counts."""
    session_id = req.session_id or str(uuid.uuid4())

    # Fetch prior turns for context continuity
    past_messages = await chat_service.get_messages(session_id, user_id=req.user_id)
    chat_history = [{"role": m.role, "content": m.content} for m in past_messages[-6:]]

    reply = ""
    model_name = "gemini-2.5-flash"
    routed_to = "orchestrator"
    user_tokens = 0
    assistant_tokens = 0

    try:
        agent_res = await agent_service.execute_agent_non_streaming(
            req.agent_id, req.prompt, chat_history=chat_history
        )
        if isinstance(agent_res, dict):
            reply = agent_res.get("content", "")
            meta = agent_res.get("metadata", {})
            model_name = agent_res.get("model") or meta.get("model", "gemini-2.5-flash")
            routed_to = agent_res.get("routed_to") or meta.get("routed_to", "frontier")
            usage = meta.get("usage", {})
            user_tokens = usage.get("prompt_tokens", 0)
            assistant_tokens = usage.get("completion_tokens", 0)
        else:
            reply = str(agent_res)
    except AgentClientError as e:
        logger.warning("Downstream agent failed (session=%s), using fallback: %s", session_id, e)
        try:
            reply = await llm_service.generate_response(req.prompt)
            model_name = "stub-llm"
            routed_to = "fallback"
        except Exception as err:
            logger.error("Fallback LLM failed: %s", err)
            raise HTTPException(status_code=502, detail=f"LLM execution failed: {err}")

    user_msg = ChatMessage(
        role="user",
        content=req.prompt,
        timestamp=datetime.now(UTC).isoformat(),
        message_id=str(uuid.uuid4()),
        tokens=user_tokens,
    )
    assistant_msg = ChatMessage(
        role="assistant",
        content=reply,
        timestamp=datetime.now(UTC).isoformat(),
        message_id=str(uuid.uuid4()),
        model=model_name,
        tokens=assistant_tokens,
        routed_to=routed_to,
    )

    await chat_service.add_messages(session_id, [user_msg, assistant_msg], user_id=req.user_id)
    if req.user_id:
        try:
            await user_service.deduct_credit(
                email=req.user_id,
                amount=1,
                tokens_used=user_tokens + assistant_tokens,
                reason=f"Chat Execution ({model_name})",
                db=chat_service.session,
            )
        except Exception as u_err:
            logger.warning("Failed to record user tokens: %s", u_err)

    return ChatResponse(session_id=session_id, message=assistant_msg)


@router.get("/stream")
async def chat_stream(
    prompt: str,
    session_id: str = "",
    agent_id: str = "",
    document_ids: str = "",
    user_id: str = "",
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service),
    llm_service: LLMService = Depends(get_llm_service),
    rag_db: AsyncSession = Depends(get_rag_db),
):
    """Stream chat response tokens using Server-Sent Events (SSE) with exact model token persistence."""
    sid = session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        full_response = ""
        use_fallback = False
        routed_to = None
        model_name = None
        complexity_score = None
        model_usage = None

        # 1. Fetch conversation history
        past_messages = await chat_service.get_messages(sid, user_id=user_id if user_id else None)
        chat_history = [{"role": m.role, "content": m.content} for m in past_messages[-6:]]

        # 2. Retrieve document context if attached
        effective_prompt = prompt
        doc_ids = [d.strip() for d in document_ids.split(",") if d.strip()]
        if doc_ids:
            try:
                matched = await rag_service.search_documents(prompt, doc_ids, top_k=4, db=rag_db)
                if matched:
                    context_block = "\n\n".join(
                        f"[Document: {c['filename']} (chunk {c['chunk_index']})]:\n{c['chunk_text']}"
                        for c in matched
                    )
                    effective_prompt = (
                        f"Relevant context from attached documents:\n"
                        f"==============================\n"
                        f"{context_block}\n"
                        f"==============================\n\n"
                        f"User Question: {prompt}\n\n"
                        f"Answer the user question using the context above when relevant."
                    )
            except Exception as rag_err:
                logger.warning("RAG context search failed: %s", rag_err)

        # 3. Stream from downstream agent service
        try:
            async for line in agent_service.execute_agent_streaming(
                agent_id if agent_id else None, effective_prompt, chat_history=chat_history
            ):
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:].strip())
                    if data.get("done"):
                        routed_to = data.get("routed_to", routed_to)
                        model_name = data.get("model", model_name)
                        model_usage = data.get("usage", model_usage)
                        yield f"data: {json.dumps({'done': True, 'session_id': sid, 'routed_to': routed_to, 'model': model_name, 'usage': model_usage})}\n\n"
                        break
                    routed_to = data.get("routed_to", routed_to)
                    model_name = data.get("model", model_name)
                    complexity_score = data.get("complexity_score", complexity_score)
                    model_usage = data.get("usage", model_usage)

                    if data.get("type") in ("routing_init", "routing_decision"):
                        yield f"data: {json.dumps(data)}\n\n"
                        continue

                    token = data.get("token", "")
                    full_response += token
                    yield f"data: {json.dumps({'token': token, 'session_id': sid, 'routed_to': routed_to, 'model': model_name})}\n\n"
                except json.JSONDecodeError:
                    pass
        except Exception as err:
            logger.warning("Agent stream failed (session=%s), using fallback: %s", sid, err)
            use_fallback = True

        # 4. Fallback streaming if agent service is unreachable
        if use_fallback:
            try:
                async for token in llm_service.stream_response(prompt):
                    full_response += token
                    yield f"data: {json.dumps({'token': token, 'session_id': sid})}\n\n"
            except Exception as fallback_err:
                logger.error("Fallback streaming failed: %s", fallback_err)
                err_msg = f"\nError: {fallback_err}"
                full_response += err_msg
                yield f"data: {json.dumps({'token': err_msg, 'session_id': sid})}\n\n"

        # 5. Extract exact token usage directly from model API response
        user_tokens = 0
        assistant_tokens = 0
        if model_usage and isinstance(model_usage, dict):
            user_tokens = model_usage.get("prompt_tokens", 0)
            assistant_tokens = model_usage.get("completion_tokens") or model_usage.get("total_tokens", 0)

        final_model = model_name or ("stub-llm" if use_fallback else "gemini-2.5-flash")
        final_routed_to = routed_to or ("fallback" if use_fallback else "frontier")

        # 6. Persist both user and assistant messages with attribution
        user_msg = ChatMessage(
            role="user",
            content=prompt,
            timestamp=datetime.now(UTC).isoformat(),
            message_id=str(uuid.uuid4()),
            tokens=user_tokens,
        )
        assistant_msg = ChatMessage(
            role="assistant",
            content=full_response,
            timestamp=datetime.now(UTC).isoformat(),
            message_id=str(uuid.uuid4()),
            model=final_model,
            tokens=assistant_tokens,
            routed_to=final_routed_to,
            complexity_score=complexity_score,
        )
        try:
            await chat_service.add_messages(sid, [user_msg, assistant_msg], user_id=user_id if user_id else None)
            if user_id:
                await user_service.deduct_credit(
                    email=user_id,
                    amount=1,
                    tokens_used=user_tokens + assistant_tokens,
                    reason=f"Chat Stream ({final_model})",
                    db=chat_service.session,
                )
        except Exception as db_err:
            logger.error("Failed to persist messages or record tokens to database: %s", db_err)

        yield f"data: {json.dumps({'done': True, 'session_id': sid, 'routed_to': final_routed_to, 'model': final_model, 'usage': model_usage})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
