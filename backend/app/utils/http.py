import logging
import time

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import install_handlers
from app.utils.limits import BodyLimitMiddleware


def configure_app(app):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    install_handlers(app)
    app.add_middleware(
        BodyLimitMiddleware, max_bytes=settings.max_audio_size_mb * 1024 * 1024 + 65536
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Upload-Ticket"],
    )

    @app.middleware("http")
    async def headers(request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        logging.getLogger("requests").info(
            "%s %s %d %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            time.monotonic() - start,
        )
        return response
