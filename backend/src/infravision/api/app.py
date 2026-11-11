"""FastAPI main application entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infravision.api.routes import router
from infravision.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize database extensions and tables on startup
    try:
        await init_db()
    except Exception as e:
        print(f"Database initialization warning (ensure Postgres is running): {e}")
    yield


app = FastAPI(
    title="Infravision Code Visualizer API",
    description="Backend graph and AST intelligence engine for Python & TypeScript/Node.js codebases",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "infravision"}
