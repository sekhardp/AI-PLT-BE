import json
import logging
import uuid
from datetime import datetime, UTC
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.v1.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.agent_service import AgentService, get_agent_service
from app.services.chat_service import ChatService, get_chat_service
from app.services.llm_service import LLMService, get_llm_service
from app.clients.agent_client import AgentClientError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """
    Execute a chat prompt. Tries to communicate with downstream Agent Service,
    falling back to local/external LLM service if downstream is unreachable.
    """
    session_id = req.session_id or str(uuid.uuid4())
    reply = ""

    try:
        # Fetch previous conversation turns from history
        past_messages = await chat_service.get_messages(session_id)
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in past_messages[-6:]
        ]
        # Try executing against downstream agent service with chat history
        reply = await agent_service.execute_agent_non_streaming(
            req.agent_id, req.prompt, chat_history=chat_history
        )
    except AgentClientError as e:
        logger.warning(
            "Downstream agent execution failed (session_id=%s). Falling back to LLM service. Error: %s",
            session_id,
            e,
        )
        try:
            reply = await llm_service.generate_response(req.prompt)
        except Exception as fallback_err:
            logger.error("Fallback LLM execution failed: %s", fallback_err)
            raise HTTPException(
                status_code=502,
                detail=f"Both agent service and fallback LLM service failed: {fallback_err}",
            )

    user_msg = ChatMessage(
        role="user",
        content=req.prompt,
        timestamp=datetime.now(UTC).isoformat(),
        message_id=str(uuid.uuid4()),
    )
    assistant_msg = ChatMessage(
        role="assistant",
        content=reply,
        timestamp=datetime.now(UTC).isoformat(),
        message_id=str(uuid.uuid4()),
    )

    await chat_service.add_messages(session_id, [user_msg, assistant_msg])

    return ChatResponse(session_id=session_id, message=assistant_msg)


@router.get("/stream")
async def chat_stream(
    prompt: str,
    session_id: str = "",
    agent_id: str = "",
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """
    Stream chat response tokens using Server-Sent Events (SSE).
    """
    sid = session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        full_response = ""
        use_fallback = False
        routed_to = None
        model_name = None

        try:
            # Fetch previous conversation turns from history for context continuity
            past_messages = await chat_service.get_messages(sid)
            chat_history = [
                {"role": m.role, "content": m.content}
                for m in past_messages[-6:]
            ]

            # 1. Attempt streaming from downstream agent service with chat history
            async for line in agent_service.execute_agent_streaming(
                agent_id if agent_id else None, prompt, chat_history=chat_history
            ):
                if line.startswith("data: "):
                    data_str = line[len("data: ") :].strip()
                    try:
                        data_json = json.loads(data_str)
                        if data_json.get("done"):
                            yield f"data: {json.dumps({'done': True, 'session_id': sid, 'routed_to': data_json.get('routed_to'), 'model': data_json.get('model')})}\n\n"
                            break
                        if data_json.get("routed_to"):
                            routed_to = data_json["routed_to"]
                        if data_json.get("model"):
                            model_name = data_json["model"]
                        if data_json.get("type") in ("routing_init", "routing_decision"):
                            yield f"data: {json.dumps({'type': data_json.get('type'), 'session_id': sid, 'stage': data_json.get('stage'), 'routed_to': data_json.get('routed_to'), 'model': data_json.get('model'), 'complexity_score': data_json.get('complexity_score'), 'fallback_triggered': data_json.get('fallback_triggered', False)})}\n\n"
                            continue
                        token = data_json.get("token", "")
                        full_response += token
                        yield f"data: {json.dumps({'token': token, 'session_id': sid, 'routed_to': data_json.get('routed_to'), 'model': data_json.get('model')})}\n\n"
                    except json.JSONDecodeError:
                        pass
        except AgentClientError as e:
            logger.warning(
                "Streaming from agent service failed (session=%s). Falling back to LLM service. Error: %s",
                sid,
                e,
            )
            use_fallback = True

        if use_fallback:
            try:
                # 2. Fallback to direct/stub LLM streaming
                async for token in llm_service.stream_response(prompt):
                    full_response += token
                    yield f"data: {json.dumps({'token': token, 'session_id': sid})}\n\n"
            except Exception as fallback_err:
                logger.error("Fallback LLM streaming failed: %s", fallback_err)
                err_msg = f"\nError: Fallback LLM failed: {fallback_err}"
                full_response += err_msg
                yield f"data: {json.dumps({'token': err_msg, 'session_id': sid})}\n\n"

        # Save both messages to history
        user_msg = ChatMessage(
            role="user",
            content=prompt,
            timestamp=datetime.now(UTC).isoformat(),
            message_id=str(uuid.uuid4()),
        )
        assistant_msg = ChatMessage(
            role="assistant",
            content=full_response,
            timestamp=datetime.now(UTC).isoformat(),
            message_id=str(uuid.uuid4()),
        )
        try:
            await chat_service.add_messages(sid, [user_msg, assistant_msg])
        except Exception as db_err:
            logger.error("Failed to persist chat messages to database: %s", db_err)

        yield f"data: {json.dumps({'done': True, 'session_id': sid, 'routed_to': routed_to, 'model': model_name})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
