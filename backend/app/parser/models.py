from pydantic import BaseModel, Field


class Column(BaseModel):
    name: str
    type: str
    length: int | None = None
    nullable: bool = True
    default: str | None = None
    primary_key: bool = False
    auto_increment: bool = False
    comment: str = ""


class Index(BaseModel):
    name: str
    unique: bool = False
    columns: list[str]


class ForeignKey(BaseModel):
    columns: list[str]
    ref_table: str
    ref_columns: list[str]


class Table(BaseModel):
    name: str
    schema_: str = Field(default="", alias="schema")
    comment: str = ""
    columns: list[Column] = []
    indexes: list[Index] = []
    foreign_keys: list[ForeignKey] = []

    model_config = {"populate_by_name": True}


class ParseError(BaseModel):
    statement_index: int
    line: int
    message: str


class ParseResult(BaseModel):
    dialect: str
    tables: list[Table] = []
    errors: list[ParseError] = []
