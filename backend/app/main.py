import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routes import auth, analysis, sessions, chat, samples, system

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

@app.get("/")
def root():
    return {
        "product": "codewise",
        "tagline": "understand the code. master the logic.",
        "docs_url": "/docs",
        "status": "online"
    }
