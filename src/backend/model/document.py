from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from src.backend.model.base import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    title = Column(String, index=True, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)

    project = relationship("Project", back_populates="documents")
    blocks = relationship(
        "DocumentBlock",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentBlock(BaseModel):
    __tablename__ = "document_blocks"

    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, default="")
    position_key = Column(String, index=True)
    type = Column(String, default="paragraph")
    last_edited_by = Column(UUID(as_uuid=True), nullable=True)

    document = relationship("Document", back_populates="blocks")

    __table_args__ = (
        UniqueConstraint("doc_id", "position_key", name="uq_doc_position"),
    )
