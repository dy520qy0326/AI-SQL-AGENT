from pydantic import BaseModel


class RelationResponse(BaseModel):
    id: str
    source_table_id: str
    source_table_name: str = ""
    source_columns: list[str]
    target_table_id: str
    target_table_name: str = ""
    target_columns: list[str]
    relation_type: str
    confidence: float
    source: str | None = None

    model_config = {"from_attributes": True}


class RelationListResponse(BaseModel):
    items: list[RelationResponse]
    total: int
