import pdfplumber
import docx
import tempfile
from fastapi import HTTPException
from langchain_openai import ChatOpenAI

from src.backend.config import settings
from . import schemas, prompts, constants


async def extract_resume_data(resume_text: str) -> schemas.ResumeExtraction:
    try:
        llm = ChatOpenAI(
            model=constants.MODEL_NAME,
            temperature=constants.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        ).with_structured_output(schemas.ResumeExtraction)

    llm = ChatOpenAI(
        model=constants.MODEL_NAME,
        temperature=constants.TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    ).with_structured_output(schemas.ResumeExtraction)

    # Simplified prompt to avoid duplication with PROMPT_TEMPLATE
    prompt = f"{prompts.PROMPT_TEMPLATE}\n\nResume Content:\n{resume_text}"

    response = await llm.ainvoke(prompt)

    return response


def parse_pdf(file_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            with pdfplumber.open(tmp.name) as pdf:
                return "".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")


def parse_docx(file_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            doc = docx.Document(tmp.name)
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX parsing failed: {str(e)}")