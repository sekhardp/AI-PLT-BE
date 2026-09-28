import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.v1.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ModelTokenItem,
    StopChatRequest,
    TierTokenSummary,
    TokenStatsResponse,
)
from app.clients.agent_client import AgentClientError
from app.db.models import ChatMessage as ChatMessageModel
from app.services.agent_service import AgentService, get_agent_service
from app.services.chat_service import ChatService, get_chat_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Active in-flight async streaming tasks keyed by session_id
_active_chat_tasks: dict[str, asyncio.Task] = {}


@router.post("/stop", tags=["Chat"])
async def stop_chat_stream(
    req: StopChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
):
    """Stop active streaming execution and cancel downstream agent task."""
    sid = req.session_id.strip() if req.session_id else ""
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")

    task = _active_chat_tasks.get(sid)
    if task and not task.done():
        logger.info("Cancelling backend chat stream task for session=%s", sid)
        task.cancel()

    # Forward cancellation to downstream agent service
    try:
        await agent_service.stop_agent(sid)
    except Exception as e:
        logger.warning("Failed notifying agent service of stop: %s", e)

    return {"status": "stopped", "session_id": sid, "message": "Chat execution stopped"}


@router.get("/token-stats", response_model=TokenStatsResponse, tags=["Chat"])
async def get_model_token_stats(
    chat_service: ChatService = Depends(get_chat_service),
):
    """Aggregate per-model and per-tier token consumption from database."""
    session = chat_service.session

    stmt = select(
        ChatMessageModel.model,
        ChatMessageModel.routed_to,
        func.count().label("message_count"),
        func.coalesce(func.sum(ChatMessageModel.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(ChatMessageModel.tokens_prompt), 0).label("prompt_tokens"),
        func.coalesce(func.sum(ChatMessageModel.tokens_completion), 0).label("completion_tokens"),
    ).group_by(ChatMessageModel.model, ChatMessageModel.routed_to)

    result = await session.execute(stmt)
    rows = result.all()

    model_map: dict[str, dict[str, Any]] = {}
    tier_map: dict[str, dict[str, Any]] = {
        "local": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "message_count": 0, "percentage": 0.0},
        "frontier": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "message_count": 0, "percentage": 0.0},
    }

    grand_total_tokens = 0
    grand_total_queries = 0

    for row in rows:
        raw_model = row.model or "unknown"
        raw_routed = row.routed_to or "frontier"
        m_count = int(row.message_count or 0)
        t_tokens = int(row.total_tokens or 0)
        p_tokens = int(row.prompt_tokens or 0)
        c_tokens = int(row.completion_tokens or 0)

        is_local = "qwen" in raw_model.lower() or raw_routed == "local"
        tier = "local" if is_local else "frontier"

        if "qwen" in raw_model.lower():
            display_name = "Qwen 3 Coder 30B (Local LLM)"
        elif "2.5-pro" in raw_model.lower():
            display_name = "Gemini 2.5 Pro (Frontier)"
        elif "2.5-flash" in raw_model.lower() or "gemini" in raw_model.lower():
            display_name = "Gemini 2.5 Flash (Frontier)"
        elif "stub" in raw_model.lower():
            display_name = "Fallback LLM"
        else:
            display_name = raw_model

        if raw_model not in model_map:
            model_map[raw_model] = {
                "model": raw_model,
                "display_name": display_name,
                "tier": tier,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "message_count": 0,
                "percentage": 0.0,
            }

        model_map[raw_model]["total_tokens"] += t_tokens
        model_map[raw_model]["prompt_tokens"] += p_tokens
        model_map[raw_model]["completion_tokens"] += c_tokens
        model_map[raw_model]["message_count"] += m_count

        tier_map[tier]["total_tokens"] += t_tokens
        tier_map[tier]["prompt_tokens"] += p_tokens
        tier_map[tier]["completion_tokens"] += c_tokens
        tier_map[tier]["message_count"] += m_count

        grand_total_tokens += t_tokens
        grand_total_queries += m_count

    by_model: list[ModelTokenItem] = []
    for item in model_map.values():
        pct = round((item["total_tokens"] / grand_total_tokens * 100), 1) if grand_total_tokens > 0 else 0.0
        item["percentage"] = pct
        by_model.append(ModelTokenItem(**item))

    for tier_key, t_data in tier_map.items():
        t_data["percentage"] = round((t_data["total_tokens"] / grand_total_tokens * 100), 1) if grand_total_tokens > 0 else 0.0

    return TokenStatsResponse(
        total_tokens=grand_total_tokens,
        total_queries=grand_total_queries,
        by_model=by_model,
        by_tier={
            "local": TierTokenSummary(**tier_map["local"]),
            "frontier": TierTokenSummary(**tier_map["frontier"]),
        },
    )


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    session_id = req.session_id or str(uuid.uuid4())

    past_messages = await chat_service.get_messages(session_id, user_id=req.user_id)
    chat_history = [{"role": m.role, "content": m.content} for m in past_messages[-6:]]

    reply = ""
    model_name = req.model or "gemini-2.5-flash"
    routed_to = "orchestrator"
    user_tokens = 0
    assistant_tokens = 0

    try:
        agent_res = await agent_service.execute_agent_non_streaming(
            req.agent_id, req.prompt, chat_history=chat_history, model=req.model, session_id=session_id
        )
        if isinstance(agent_res, dict):
            reply = agent_res.get("content", "")
            meta = agent_res.get("metadata", {})
            model_name = agent_res.get("model") or meta.get("model", req.model or "gemini-2.5-flash")
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
        model=model_name,
        routed_to=routed_to,
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
    model: str = "",
    document_ids: str = "",
    user_id: str = "",
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Stream chat response tokens using Server-Sent Events (SSE) with exact model token persistence."""
    sid = session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        current_task = asyncio.current_task()
        if sid and current_task:
            _active_chat_tasks[sid] = current_task

        full_response = ""
        use_fallback = False
        routed_to = None
        model_name = model if model else None
        complexity_score = None
        model_usage = None

        try:
            # 1. Fetch conversation history
            past_messages = await chat_service.get_messages(sid, user_id=user_id if user_id else None)
            chat_history = [{"role": m.role, "content": m.content} for m in past_messages[-6:]]

            # 2. Forward prompt with context continuity
            effective_prompt = prompt
            doc_ids = [d.strip() for d in document_ids.split(",") if d.strip()]
            if doc_ids:
                effective_prompt = f"{prompt}\n\n[Attached Document IDs: {', '.join(doc_ids)}]"

            # 3. Stream from downstream agent service
            try:
                async for line in agent_service.execute_agent_streaming(
                    agent_id if agent_id else None,
                    effective_prompt,
                    chat_history=chat_history,
                    model=model if model else None,
                    session_id=sid,
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

                        if data.get("type") in ("routing_init", "routing_decision", "tool_start", "tool_done", "step_update"):
                            yield f"data: {json.dumps(data)}\n\n"
                            continue

                        token = data.get("token", "")
                        full_response += token
                        yield f"data: {json.dumps({'token': token, 'session_id': sid, 'routed_to': routed_to, 'model': model_name})}\n\n"
                    except json.JSONDecodeError:
                        pass
            except asyncio.CancelledError:
                logger.info("Client cancelled stream for session=%s", sid)
                yield f"data: {json.dumps({'done': True, 'stopped': True, 'session_id': sid})}\n\n"
                return
            except Exception as err:
                logger.warning("Agent stream failed (session=%s), using fallback: %s", sid, err)
                use_fallback = True

            # 4. Fallback streaming if agent service is unreachable
            if use_fallback:
                try:
                    async for token in llm_service.stream_response(prompt):
                        full_response += token
                        yield f"data: {json.dumps({'token': token, 'session_id': sid})}\n\n"
                except asyncio.CancelledError:
                    return
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
                model=final_model,
                routed_to=final_routed_to,
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
        finally:
            if sid and _active_chat_tasks.get(sid) is current_task:
                _active_chat_tasks.pop(sid, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
