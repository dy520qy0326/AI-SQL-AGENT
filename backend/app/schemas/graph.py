from pydantic import BaseModel, Field


class ColumnBrief(BaseModel):
    name: str
    type: str
    pk: bool = False
    fk: bool = False


class GraphNode(BaseModel):
    id: str
    label: str
    schema_name: str = ""
    column_count: int = 0
    columns: list[ColumnBrief] = []


class GraphEdge(BaseModel):
    id: str
    from_: str = Field(default="", alias="from")
    to: str = ""
    label: str = ""
    type: str = "FOREIGN_KEY"
    confidence: float = 1.0
    dashes: bool = False

    model_config = {"populate_by_name": True}


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
