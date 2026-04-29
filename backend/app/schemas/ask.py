from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None


class AskSource(BaseModel):
    table: str
    column: str | None = None
    description: str | None = None


class AskSyncResponse(BaseModel):
    answer: str
    sources: list[AskSource] = []
    session_id: str
