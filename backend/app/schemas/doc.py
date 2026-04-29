from pydantic import BaseModel


class DocGenerateRequest(BaseModel):
    ai_enhance: bool = True
    title: str | None = None


class DocResponse(BaseModel):
    id: str
    project_id: str
    doc_type: str
    title: str
    ai_enhanced: bool
    created_at: str
    content_snippet: str


class DocListResponse(BaseModel):
    items: list[DocResponse]
    total: int
