from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, model_validator

from app.services.presentation import (
    ChartConfig,
    ChartSeries,
    KPICard,
    Slide,
    SlideDeck,
    TableConfig,
)

__all__ = [
    "KPICard",
    "ChartSeries",
    "ChartConfig",
    "TableConfig",
    "Slide",
    "SlideDeck",
    "PresentationExportBase64Request",
    "PresentationExportDeckRequest",
]


class PresentationExportBase64Request(BaseModel):
    base64_data: str = Field(..., description="Base64 encoded binary presentation data")
    filename: str | None = Field(None, description="Optional custom filename")


class PresentationExportDeckRequest(BaseModel):
    deck: SlideDeck = Field(..., description="Structured SlideDeck JSON schema")
    filename: str | None = Field(None, description="Optional custom filename")

    @model_validator(mode="before")
    @classmethod
    def _normalize_request(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_deck = data.get("deck")
            if isinstance(raw_deck, dict):
                data["deck"] = SlideDeck.model_validate(raw_deck)
        return data
