from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class KPICard(BaseModel):
    label: str = Field(..., description="Metric label")
    value: str = Field(..., description="Metric value (e.g. '$4.2M')")
    change: str | None = Field(None, description="Delta (e.g. '+14.2% YoY')")
    trend: Literal["up", "down", "neutral"] | None = Field("up", description="Trend direction")


class ChartSeries(BaseModel):
    name: str
    values: list[float | int]


class ChartConfig(BaseModel):
    chart_type: Literal["bar", "horizontal_bar", "line", "pie", "doughnut"] = "bar"
    title: str | None = None
    categories: list[str]
    series: list[ChartSeries]


class TableConfig(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class Slide(BaseModel):
    slide_number: int
    layout: Literal[
        "title_slide",
        "kpi_grid",
        "chart_and_bullets",
        "two_column_comparison",
        "table_slide",
        "bullet_cards",
    ]
    title: str
    subtitle: str | None = None
    bullet_points: list[str] = Field(default_factory=list)
    kpi_cards: list[KPICard] = Field(default_factory=list)
    chart: ChartConfig | None = None
    table: TableConfig | None = None
    left_column_title: str | None = None
    left_column_bullets: list[str] = Field(default_factory=list)
    right_column_title: str | None = None
    right_column_bullets: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class SlideDeck(BaseModel):
    deck_title: str
    deck_subtitle: str | None = None
    theme: Literal["dark", "light", "midnight", "navy", "emerald"] = "dark"
    author: str | None = "AI Platform"
    slides: list[Slide]
    sources_summary: list[str] = Field(default_factory=list)


class PresentationExportBase64Request(BaseModel):
    base64_data: str = Field(..., description="Base64 encoded binary presentation data")
    filename: str | None = Field(None, description="Optional custom filename")


class PresentationExportDeckRequest(BaseModel):
    deck: SlideDeck = Field(..., description="Structured SlideDeck JSON schema")
    filename: str | None = Field(None, description="Optional custom filename")
