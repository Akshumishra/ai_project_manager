from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from src.backend.collaborative_document import schemas, services
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user import User

router = APIRouter(prefix="/api/block", tags=["blocks"])


@router.post("/documents/{document_id}")
async def insert_block(
    document_id: UUID,
    data: schemas.BlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.insert_block(document_id, data, db, current_user)


@router.patch("/{block_id}")
async def edit_block(
    block_id: UUID,
    data: schemas.BlockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.edit_block(str(block_id), data, db, current_user)


@router.delete("/{block_id}")
async def delete_block(
    block_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await services.delete_block(str(block_id), db, current_user)
