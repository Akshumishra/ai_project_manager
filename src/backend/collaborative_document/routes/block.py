from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.collaborative_document.services import document
from src.backend.collaborative_document import schemas
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User

router = APIRouter(prefix="/api/block", tags=["blocks"])


@router.post(
    "/documents/{document_id}",
    response_model=schemas.BlockCreateResponse,
    status_code=201
)
async def insert_block(
    document_id: UUID,
    data: schemas.BlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await document.insert_block(document_id, data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert block: {str(e)}"
        )


@router.patch(
    "/{block_id}",
    response_model=schemas.MessageResponse,
    status_code=200
)
async def edit_block(
    block_id: UUID,
    data: schemas.BlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await document.edit_block(str(block_id), data, db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to edit block: {str(e)}"
        )


@router.delete(
    "/{block_id}",
    response_model=schemas.MessageResponse,
    status_code=200
)
async def delete_block(
    block_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await document.delete_block(str(block_id), db, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete block: {str(e)}"
        )
