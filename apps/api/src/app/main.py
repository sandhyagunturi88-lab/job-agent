from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.graph.build import build_graph
from app.graph.checkpointer import open_checkpointer
from app.routers import me, runs, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with open_checkpointer(settings) as checkpointer:
        app.state.graph = build_graph(checkpointer=checkpointer)
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="JobPilot UK API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(runs.router)
    app.include_router(me.router)
    app.include_router(ws.router)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
