"""
Unifile by Soniscorett - Web Application Server
Serves the REST API, MCP endpoints, and interactive Cyber-Clean Web Dashboard.
"""

from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .connectors.api_routes import router as api_router

STATIC_DIR = Path(__file__).parent.parent / "static"

app = FastAPI(
    title="Unifile by Soniscorett",
    description="Universal Read-Only File Translator Connector for AI Models.",
    version="2.4.0",
)

# Enforce read-only guarantees and security headers across all network interfaces
@app.middleware("http")
async def enforce_read_only_and_security_headers(request: Request, call_next):
    # Strictly reject any write/mutation HTTP methods
    if request.method in ("PUT", "DELETE", "PATCH"):
        return JSONResponse(
            status_code=405,
            content={
                "error": "Method Not Allowed",
                "message": f"Method '{request.method}' is prohibited. Unifile by Soniscorett is strictly READ-ONLY.",
                "read_only": True
            }
        )
    
    response = await call_next(request)
    
    # Attach audit and security headers
    response.headers["X-Unifile-Mode"] = "STRICT_READ_ONLY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # HSTS is emitted only when the application itself sees HTTPS.
    if request.url.scheme.lower() == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Restrict CORS to safe read/query HTTP methods only, with configurable origin allowlist
allowed_origins_env = os.environ.get(
    "UNIFILE_CORS_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000",
)
origins = [o.strip() for o in (allowed_origins_env.split(",") if allowed_origins_env != "*" else ["*"])]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Credentials are opt-in and cannot be combined with wildcard origins.
    allow_credentials=(
        os.environ.get("UNIFILE_CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
        and "*" not in origins
    ),
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# Mount REST API
app.include_router(api_router)

# Mount static web files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    @app.head("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico")
    @app.head("/favicon.ico")
    async def favicon():
        fav_path = STATIC_DIR / "assets" / "favicon.svg"
        if fav_path.exists():
            return FileResponse(fav_path)
        return FileResponse(STATIC_DIR / "assets" / "unifile-icon.svg")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unifile.server:app", host="127.0.0.1", port=8000, reload=False)
