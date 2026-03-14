from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.collaborative_document import schemas, services
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/")
def create_document(
    data: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.create_document(data, db, current_user)


@router.get("/{document_id}")
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.get_document(document_id, db, current_user)
