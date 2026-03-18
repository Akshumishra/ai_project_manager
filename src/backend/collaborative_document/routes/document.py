from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.collaborative_document.services import document
from src.backend.collaborative_document import schemas
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post(
    "/",
    response_model=schemas.DocumentCreateResponse,
    status_code=201
)
def create_document(
    data: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return document.create_document(data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}"
        )


@router.get(
    "/{document_id}",
    response_model=schemas.DocumentDetailResponse,
    status_code=200
)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return document.get_document(document_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document: {str(e)}"
        )


@router.patch(
    "/{document_id}",
    response_model=schemas.DocumentResponse,
    status_code=200
)
def update_document(
    document_id: UUID, 
    data: schemas.DocumentUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return document.update_document(document_id, data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {str(e)}"
        )


@router.delete(
    "/{document_id}",
    response_model=schemas.MessageResponse,
    status_code=200
)
def delete_document(
    document_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return document.delete_document(document_id, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )
