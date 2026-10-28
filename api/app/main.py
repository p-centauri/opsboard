import logging
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_engine
from app.errors import register_error_handlers
from app.routers import analytics, audit_log, auth, customers, orders, products, users

logger = logging.getLogger(__name__)

app = FastAPI(title="OpsBoard API")
register_error_handlers(app)
for router in (auth, customers, products, orders, analytics, users, audit_log):
    app.include_router(router.router)


@app.get("/health")
def health(engine: Annotated[Engine, Depends(get_engine)]) -> JSONResponse:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "db_unavailable", "message": "Database unavailable"}},
        )
    return JSONResponse({"status": "ok"})
