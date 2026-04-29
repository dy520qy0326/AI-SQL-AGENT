from pydantic import BaseModel, Field


class RelationItem(BaseModel):
    source_table: str
    source_columns: list[str]
    target_table: str
    target_columns: list[str]
    relation_type: str
    confidence: float
    source: str | None = None


class CompleteRelationsResponse(BaseModel):
    new_relations: int
    relations: list[RelationItem] = []
    cache_hit: bool = False
    message: str = ""


class CommentFieldItem(BaseModel):
    table: str
    column: str
    comment: str


class CompleteCommentsResponse(BaseModel):
    updated: int
    fields: list[CommentFieldItem] = []
    cache_hit: bool = False
    message: str = ""


class AIStatusResponse(BaseModel):
    ai_enabled: bool
    ai_model: str
    cache_count: int = 0
    last_completion: str | None = None


class CacheClearResponse(BaseModel):
    deleted_count: int
    message: str = "cache cleared"
