from datetime import datetime

from pydantic import BaseModel


class ColumnResponse(BaseModel):
    id: str
    name: str
    data_type: str
    length: int | None = None
    nullable: bool = True
    default_value: str | None = None
    is_primary_key: bool = False
    ordinal_position: int = 0
    comment: str | None = None

    model_config = {"from_attributes": True}


class IndexResponse(BaseModel):
    id: str
    name: str
    unique: bool = False
    columns: list[str]

    model_config = {"from_attributes": True}


class ForeignKeyResponse(BaseModel):
    id: str
    columns: list[str]
    ref_table_name: str
    ref_columns: list[str]
    constraint_name: str | None = None

    model_config = {"from_attributes": True}


class TableResponse(BaseModel):
    id: str
    name: str
    schema_name: str = ""
    comment: str | None = None
    column_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TableDetailResponse(BaseModel):
    id: str
    name: str
    schema_name: str = ""
    comment: str | None = None
    columns: list[ColumnResponse] = []
    indexes: list[IndexResponse] = []
    foreign_keys: list[ForeignKeyResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
