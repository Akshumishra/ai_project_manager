from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class DocumentCreate(BaseModel):
    title: str
    project_id: UUID


class BlockCreate(BaseModel):
    content: str
    type: str = "paragraph"
    prev_block_id: UUID | None = None
    next_block_id: UUID | None = None
    client_id: str | None = None
    position_key: str | None = None


class BlockUpdate(BaseModel):
    content: str
    type: str | None = None


class DocumentUpdate(BaseModel):
    title: str
