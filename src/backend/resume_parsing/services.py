import pdfplumber
import docx
from io import BytesIO
from fastapi import HTTPException
from langchain_openai import ChatOpenAI

from src.backend.config import settings
from . import schemas, prompts, constants


def extract_resume_data(resume_text: str) -> schemas.ResumeExtraction:
    try:
        llm = ChatOpenAI(
            model=constants.MODEL_NAME,
            temperature=constants.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        ).with_structured_output(schemas.ResumeExtraction)

        prompt = prompts.PROMPT_TEMPLATE.format(resume=resume_text)

        response =  llm.invoke(prompt)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {str(e)}")

def parse_file(file_bytes: bytes, filename: str) -> str:
    try:
        filename = filename.lower()

        if filename.endswith(".pdf"):
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)

        elif filename.endswith(".docx"):
            doc = docx.Document(BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)

        elif filename.endswith(".txt"):
            return file_bytes.decode("utf-8")

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File parsing failed: {str(e)}")