import logging
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_engine

logger = logging.getLogger(__name__)

app = FastAPI(title="OpsBoard API")


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
