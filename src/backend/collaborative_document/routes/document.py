from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.collaborative_document.services import document
from src.backend.collaborative_document import schemas
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/", response_model=schemas.DocumentCreateResponse)
def create_document(
    data: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return document.create_document(data, db, current_user)


@router.get("/{document_id}", response_model=schemas.DocumentDetailResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return document.get_document(document_id, db, current_user)


@router.patch("/{document_id}", response_model=schemas.DocumentResponse)
def update_document(
    document_id: UUID, 
    data: schemas.DocumentUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return document.update_document(document_id, data, db, current_user)


@router.delete("/{document_id}", response_model=schemas.MessageResponse)
def delete_document(
    document_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return document.delete_document(document_id, db, current_user)
