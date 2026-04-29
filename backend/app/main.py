from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.ai import router as ai_router
from app.api.diff import router as diff_router
from app.api.graph import router as graph_router
from app.api.projects import router as projects_router
from app.api.relations import router as relations_router
from app.api.sessions import router as sessions_router
from app.api.tables import router as tables_router
from app.config import settings
from app.db.engine import init_db
from app.docgen.router import router as docgen_router
from app.nl.router import router as nl_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.include_router(projects_router)
app.include_router(tables_router)
app.include_router(diff_router)
app.include_router(relations_router)
app.include_router(graph_router)
app.include_router(ai_router)
app.include_router(nl_router)
app.include_router(sessions_router)
app.include_router(docgen_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
