from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID
from . import schemas, services
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
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    return services.get_document(document_id, db)


block_router = APIRouter(prefix="/api/block", tags=["blocks"])


@block_router.post("/documents/{document_id}")
async def insert_block(
    document_id: UUID, data: schemas.BlockCreate, db: Session = Depends(get_db)
):
    return await services.insert_block(document_id, data, db)


@block_router.patch("/{block_id}")
async def edit_block(
    block_id: str, data: schemas.BlockUpdate, db: Session = Depends(get_db)
):
    return await services.edit_block(block_id, data, db)


@block_router.delete("/{block_id}")
async def delete_block(block_id: str, db: Session = Depends(get_db)):
    return await services.delete_block(block_id, db)
