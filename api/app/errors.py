"""One error shape for every failure: {"error": {"code", "message", "fields"?}}."""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, fields: dict[str, str] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields


def not_found(entity: str) -> ApiError:
    return ApiError(404, "not_found", f"{entity} not found")


def violated_constraint(error: IntegrityError) -> str | None:
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def _body(code: str, message: str, fields: dict[str, str] | None = None) -> dict[str, object]:
    error: dict[str, object] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return {"error": error}


def _field_path(loc: tuple[int | str, ...]) -> str:
    # Drop the "body"/"query"/"path" prefix: clients map errors onto their own field names.
    parts = loc[1:] if loc and loc[0] in ("body", "query", "path") else loc
    return ".".join(str(part) for part in parts) or "request"


async def _api_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApiError):  # handlers are registered per type
        raise exc
    return JSONResponse(_body(exc.code, exc.message, exc.fields), status_code=exc.status)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # handlers are registered per type
        raise exc
    fields: dict[str, str] = {}
    for err in exc.errors():
        fields.setdefault(_field_path(tuple(err["loc"])), err["msg"])
    return JSONResponse(
        _body("validation_error", "Some fields are invalid", fields), status_code=422
    )


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # handlers are registered per type
        raise exc
    code = HTTPStatus(exc.status_code).phrase.lower().replace(" ", "_")
    return JSONResponse(
        _body(code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers
    )


async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(_body("internal_error", "Something went wrong"), status_code=500)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled_error)
