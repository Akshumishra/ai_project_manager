from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from . import  services, schemas
from src.backend.db.database import get_db
import logging
from src.backend.auth.utils import get_current_user
from src.backend.model.user_detail import UserDetail
from src.backend.auth.schemas import UserDetailUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["resume"])

@router.post(
    "/parse-resume", 
    response_model=schemas.ResumeExtraction,
    status_code=status.HTTP_200_OK
)
def parse_resume(file: UploadFile = File(...)):
    try:
        content = file.file.read()
        text = services.parse_file(content, file.filename)
        return services.extract_resume_data(text)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raise HTTPException(500, f"Unexpected error: {str(e)}")

@router.post(
    "/update-profile",
    response_model= schemas.MessageResponse,
    status_code=status.HTTP_200_OK
)

def update_profile(
    data: UserDetailUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Step 2: Save reviewed/edited data to the database.
    """
    try:
        user_detail = db.query(UserDetail).filter_by(user_id=current_user.id).first()

        if not user_detail:
            user_detail = UserDetail(user_id=current_user.id)
            db.add(user_detail)

        user_detail.skills = ", ".join(data.skills or [])
        user_detail.experience = str(data.yoe)
        user_detail.designation = data.designation

        db.commit()
        return {"message": "Profile updated successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
