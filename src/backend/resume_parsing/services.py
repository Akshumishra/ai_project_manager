import pdfplumber
import docx
import tempfile
from langchain_openai import ChatOpenAI

from src.backend.config import settings
from . import schemas, prompts, constants


async def extract_resume_data(resume_text: str) -> schemas.ResumeExtraction:

    llm = ChatOpenAI(
        model=constants.MODEL_NAME,
        temperature=constants.TEMPERATURE,
        api_key=settings.OPENAI_API_KEY
    ).with_structured_output(schemas.ResumeExtraction)

    prompt = prompts.PROMPT_TEMPLATE.format(resume=resume_text)

    response = await llm.ainvoke(prompt)

    return response


def parse_pdf(file_bytes):
    with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        with pdfplumber.open(tmp.name) as pdf:
            return "".join(p.extract_text() or "" for p in pdf.pages)


def parse_docx(file_bytes):
    with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        doc = docx.Document(tmp.name)
        return "\n".join(p.text for p in doc.paragraphs)