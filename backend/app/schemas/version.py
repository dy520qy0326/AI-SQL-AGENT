from pydantic import BaseModel


class VersionCreateRequest(BaseModel):
    sql_content: str
    version_tag: str | None = None


class VersionResponse(BaseModel):
    id: str
    project_id: str
    version_tag: str | None = None
    file_hash: str
    tables_count: int = 0
    created_at: str | None = None


class VersionListResponse(BaseModel):
    items: list[VersionResponse]
    total: int


class DiffRequest(BaseModel):
    old_version_id: str
    new_version_id: str


class DiffResponse(BaseModel):
    id: str
    project_id: str
    old_version_id: str
    new_version_id: str
    diff_data: dict
    summary: str | None = None
    breaking_changes: bool = False
    created_at: str | None = None


class DiffListResponse(BaseModel):
    items: list[DiffResponse]
    total: int
