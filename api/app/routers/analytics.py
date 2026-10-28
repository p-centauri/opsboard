from typing import Annotated

from fastapi import APIRouter, Query

from app.deps import Db, Viewer
from app.schemas.analytics import (
    AnalyticsRange,
    StatusCount,
    SummaryOut,
    TopProduct,
    TopProductsParams,
    TrendOut,
    TrendParams,
)
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(params: Annotated[AnalyticsRange, Query()], db: Db, _: Viewer) -> SummaryOut:
    return analytics.summary(db, params)


@router.get("/revenue-trend")
def revenue_trend(params: Annotated[TrendParams, Query()], db: Db, _: Viewer) -> TrendOut:
    return analytics.revenue_trend(db, params)


@router.get("/top-products")
def top_products(
    params: Annotated[TopProductsParams, Query()], db: Db, _: Viewer
) -> list[TopProduct]:
    return analytics.top_products(db, params, params.limit)


@router.get("/status-breakdown")
def status_breakdown(
    params: Annotated[AnalyticsRange, Query()], db: Db, _: Viewer
) -> list[StatusCount]:
    return analytics.status_breakdown(db, params)
