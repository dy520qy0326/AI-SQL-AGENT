from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    dialect: str = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    dialect: str
    table_count: int = 0
    relation_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    size: int


class UploadRequest(BaseModel):
    sql_content: str = Field(..., min_length=1)


class ErrorItem(BaseModel):
    statement_index: int
    line: int
    message: str


class UploadResponse(BaseModel):
    tables_count: int
    relations_count: int
    errors: list[ErrorItem] = []
