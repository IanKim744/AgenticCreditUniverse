from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Universe = Literal["O", "△", "X"]


class CompanyRow(BaseModel):
    slug: str
    issuer: str
    stock_code: Optional[str] = None
    group_name: Optional[str] = None
    industry: Optional[str] = None
    industry_2026: Optional[str] = None
    rating_prev: Optional[str] = None
    watch_prev: Optional[str] = None
    rating_curr: Optional[str] = None
    watch_curr: Optional[str] = None
    universe_prev: Optional[Universe] = None
    universe_curr_ai: Optional[Universe] = None
    reviewer_final: Optional[Universe] = None
    movement: Optional[str] = None  # "▲" / "▽" / "-" / "" / null
    comment_preview: Optional[str] = None
    manager: Optional[str] = None
    review_status: Literal["done", "none"] = "none"
    unresolved: bool = False
    last_updated_utc: Optional[str] = None


class KpiRatingDist(BaseModel):
    high: int = 0
    mid: int = 0
    low: int = 0
    nr: int = 0


class KpiMovement(BaseModel):
    up: int = 0
    down: int = 0
    flat: int = 0


class KpiReview(BaseModel):
    done: int = 0
    none: int = 0
    pct: float = 0.0


class Kpis(BaseModel):
    total: int
    rating_distribution: KpiRatingDist
    movement: KpiMovement
    review: KpiReview


class CompaniesResponse(BaseModel):
    period: dict[str, Any]
    rows: list[CompanyRow]
    kpis: Kpis


class ReviewIn(BaseModel):
    universe: Universe
    agree_with_ai: bool = False
    note: Optional[str] = Field(default=None, max_length=2000)


class ReviewStatus(BaseModel):
    status: Literal["done", "none"] = "none"
    universe: Optional[Universe] = None
    agree_with_ai: Optional[bool] = None
    note: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


class LoginIn(BaseModel):
    username: str
    password: str


class CompanyDetail(BaseModel):
    period: dict[str, Any]
    master: dict[str, Any]
    excel: dict[str, Any]
    comment: Optional[dict[str, Any]] = None
    stage2: Optional[dict[str, Any]] = None
    inversion: Optional[dict[str, Any]] = None
    nice: dict[str, Any]
    dart: dict[str, Any]
    news: dict[str, Any]
    review_status: ReviewStatus
    history: list[dict[str, Any]] = []
