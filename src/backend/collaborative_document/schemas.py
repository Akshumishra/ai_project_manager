from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List


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


class BlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    block_id: str
    position_key: str
    content: str
    type: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: str
    title: str


class DocumentDetailResponse(DocumentResponse):
    blocks: List[BlockResponse]


class DocumentCreateResponse(BaseModel):
    document_id: str
    initial_block_id: str


class BlockCreateResponse(BaseModel):
    block_id: str
    position_key: str
    client_id: str | None = None


class MessageResponse(BaseModel):
    message: str
