from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
from . import  services
from src.backend.db.database import get_db
from src.backend.auth.utils import get_current_user
from src.backend.model.user_detail import UserDetail
from src.backend.auth.schemas import UserDetailUpdate

router = APIRouter(prefix="/api/users", tags=["resume"])


@router.post("/parse-resume")
async def parse_resume(
    file: UploadFile = File(...),
):
    """
    Step 1: Extract data from resume and return JSON for review.
    Does NOT save to database yet.
    """
    filename = file.filename.lower()
    content = await file.read()

    if filename.endswith(".pdf"):
        text = await asyncio.to_thread(services.parse_pdf, content)
    elif filename.endswith(".docx"):
        text = await asyncio.to_thread(services.parse_docx, content)
    elif filename.endswith(".txt"):
        text = content.decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    result = await services.extract_resume_data(text)
    return result.model_dump()


@router.post("/update-profile")
def update_profile(
    data: UserDetailUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Step 2: Save reviewed/edited data to the database.
    """
    user_detail = (
        db.query(UserDetail).filter(UserDetail.user_id == current_user.id).first()
    )
    skills_str = ", ".join(data.skills) if data.skills else ""

    if not user_detail:
        user_detail = UserDetail(
            user_id=current_user.id,
            skills=skills_str,
            experience=data.experience_years,
            designation=data.designation,
        )
        db.add(user_detail)
    else:
        user_detail.skills = skills_str
        user_detail.experience = data.experience_years
        user_detail.designation = data.designation

    db.commit()
    return {"message": "Profile updated successfully"}
