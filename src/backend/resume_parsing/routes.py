from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import asyncio
import logging
from . import services
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user_detail import UserDetail
from src.backend.auth.schemas import UserDetailUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["resume"])


@router.post(
    "/parse-resume",
    response_model=services.schemas.ResumeExtraction,
    status_code=status.HTTP_200_OK
)
async def parse_resume(
    file: UploadFile = File(...),
):
    """
    Step 1: Extract data from resume and return JSON for review.
    Does NOT save to database yet.
    """
    try:
        filename = file.filename.lower()
        content = await file.read()

        if filename.endswith(".pdf"):
            text = await asyncio.to_thread(services.parse_pdf, content)
        elif filename.endswith(".docx"):
            text = await asyncio.to_thread(services.parse_docx, content)
        elif filename.endswith(".txt"):
            text = content.decode("utf-8")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Unsupported file type"
            )

        result = await services.extract_resume_data(text)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/update-profile",
    response_model=services.schemas.MessageResponse,
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
        user_detail = (
            db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
        )
        skills_str = ", ".join(data.skills) if data.skills else ""

        # Sync with updated UserDetail schema
        if not user_detail:
            user_detail = UserDetail(
                user_id=current_user.id,
                skills=skills_str,
                experience_years=str(data.yoe),
                designation=data.designation,
            )
            db.add(user_detail)
        else:
            user_detail.skills = skills_str
            user_detail.experience_years = str(data.yoe)
            user_detail.designation = data.designation

        db.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Profile updated successfully"}
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
