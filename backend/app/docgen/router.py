import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.docgen.generator import generate_markdown
from app.schemas.doc import DocGenerateRequest, DocListResponse, DocResponse
from app.store.repository import Repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["docs"])


@router.post("/projects/{project_id}/docs", status_code=201, response_model=DocResponse)
async def create_doc(project_id: str, body: DocGenerateRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project = await repo.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await generate_markdown(project_id, db, ai_enhance=body.ai_enhance)

    # Determine title
    title = body.title
    if not title:
        project_name = project["name"]
        suffix = " (AI增强)" if body.ai_enhance else ""
        title = f"{project_name} 数据字典{suffix}"

    doc = await repo.create_doc(
        project_id=project_id,
        doc_type="markdown",
        title=title,
        content=content,
        ai_enhanced=body.ai_enhance,
    )
    await db.commit()

    snippet = content[:200]
    return DocResponse(
        id=doc.id,
        project_id=doc.project_id,
        doc_type=doc.doc_type,
        title=doc.title,
        ai_enhanced=doc.ai_enhanced,
        created_at=doc.created_at.isoformat(),
        content_snippet=snippet,
    )


@router.get("/projects/{project_id}/docs", response_model=DocListResponse)
async def list_docs(project_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    project = await repo.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = await repo.list_docs(project_id)
    items = [
        DocResponse(
            id=d.id,
            project_id=d.project_id,
            doc_type=d.doc_type,
            title=d.title,
            ai_enhanced=d.ai_enhanced,
            created_at=d.created_at.isoformat(),
            content_snippet=d.content[:200],
        )
        for d in docs
    ]
    return DocListResponse(items=items, total=len(items))


@router.get("/projects/{project_id}/docs/{doc_id}")
async def get_doc(project_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    doc = await repo.get_doc(doc_id)
    if doc is None or doc.project_id != project_id:
        raise HTTPException(status_code=404, detail="Document not found")

    return PlainTextResponse(content=doc.content, media_type="text/markdown; charset=utf-8")


@router.delete("/projects/{project_id}/docs/{doc_id}", status_code=204)
async def delete_doc(project_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    doc = await repo.get_doc(doc_id)
    if doc is None or doc.project_id != project_id:
        raise HTTPException(status_code=404, detail="Document not found")

    await repo.delete_doc(doc_id)
    await db.commit()
