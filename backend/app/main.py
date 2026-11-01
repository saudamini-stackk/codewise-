import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routes import auth, analysis, sessions, chat, samples, system, practice

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("codewise")

# Ensure database is initialized on import
init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing codewise persistent database...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("codewise backend shutting down.")

app = FastAPI(
    title="codewise API",
    description="understand the code. master the logic. AI and static code explanation & learning assistant.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows local dev from Vite and other local hosts
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(samples.router)
app.include_router(system.router)
app.include_router(practice.router)

from pathlib import Path
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
        return FileResponse(DIST_DIR / "index.html")
    return {
        "product": "codewise",
        "tagline": "understand the code. master the logic.",
        "docs_url": "/docs",
        "status": "online"
    }

if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
    if (DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str, request: Request):
        if full_path in ("docs", "redoc", "openapi.json") or full_path.startswith("api"):
            from starlette.exceptions import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = DIST_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        if "text/html" in request.headers.get("accept", ""):
            return FileResponse(DIST_DIR / "index.html")
        from starlette.exceptions import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
