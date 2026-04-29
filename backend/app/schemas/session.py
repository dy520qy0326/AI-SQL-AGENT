from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    project_id: str
    title: str | None = None


class SessionResponse(BaseModel):
    id: str
    project_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: list | None = None
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
