from __future__ import annotations

import base64
import io
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.v1.schemas.presentation import (
    PresentationExportBase64Request,
    PresentationExportDeckRequest,
)
from app.services.presentation import PPTXBuilder

router = APIRouter()


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[-\s]+", "_", clean) or "presentation"


@router.post(
    "/export/base64",
    summary="Export Base64 Data to Downloadable PPTX Binary",
    description="Accepts base64-encoded presentation data from the PPT MCP server and streams the .pptx file.",
)
async def export_pptx_from_base64(request: PresentationExportBase64Request) -> StreamingResponse:
    try:
        raw_bytes = base64.b64decode(request.base64_data)
        stream = io.BytesIO(raw_bytes)
        clean_name = _sanitize_filename(request.filename or "presentation")
        filename = f"{clean_name}.pptx" if not clean_name.endswith(".pptx") else clean_name

        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode presentation: {e}") from e


@router.post(
    "/export/pptx",
    summary="Export SlideDeck Schema to Downloadable PPTX File",
    description="Compiles structured SlideDeck JSON into a 16:9 widescreen PowerPoint file with native charts.",
)
async def export_pptx_from_deck(request: PresentationExportDeckRequest) -> StreamingResponse:
    try:
        builder = PPTXBuilder(theme_name=request.deck.theme)
        stream = builder.build_deck(request.deck)
        clean_name = _sanitize_filename(request.filename or request.deck.deck_title)
        filename = f"{clean_name}.pptx" if not clean_name.endswith(".pptx") else clean_name

        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export presentation: {e}") from e
