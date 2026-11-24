from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routers import auth, coach, me, nutrition, training

MAX_BODY = 256 * 1024  # bytes; no endpoint needs more


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Setwise API", version="1.0.0",
                  docs_url=None if s.is_prod else "/docs", redoc_url=None, openapi_url=None if s.is_prod else "/openapi.json")

    if s.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in s.cors_origins.split(",")],
                           allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def guard(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"  # health data must not sit in caches
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if s.is_prod:
            resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return resp

    @app.get("/health")
    def health():
        return {"ok": True}

    for r in (auth.router, me.router, training.router, nutrition.router, coach.router):
        app.include_router(r)
    return app


app = create_app()
