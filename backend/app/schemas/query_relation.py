from pydantic import BaseModel


class QueryRelationRequest(BaseModel):
    sql: str


class QueryRelationPreview(BaseModel):
    temp_id: str
    source_table: str
    source_columns: list[str]
    target_table: str
    target_columns: list[str]
    join_type: str
    confidence: float
    already_exists: bool = False


class QueryRelationResponse(BaseModel):
    dialect: str
    queries_parsed: int
    relations: list[QueryRelationPreview]
    unmatched_tables: list[str]


class SaveRelationRequest(BaseModel):
    sql: str
    relation_ids: list[str]


class SaveRelationItem(BaseModel):
    id: str
    source_table: str
    source_columns: list[str]
    target_table: str
    target_columns: list[str]
    relation_type: str
    confidence: float


class SaveRelationResponse(BaseModel):
    saved: int
    skipped: int
    relations: list[SaveRelationItem]
