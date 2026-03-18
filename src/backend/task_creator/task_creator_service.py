from datetime import datetime, timezone
import json
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from src.backend.db.database import SessionLocal
from langchain_openai import ChatOpenAI

from src.backend.model.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskComplexity
from src.backend.model.document import Document, DocumentBlock
from src.backend.config import settings
from src.backend.task_creator.constants import TaskCreatorConstants
from src.backend.task_creator.task_creator_agent.prompt import (
    system_prompt,
    user_prompt
)
from .task_creator_agent.agent import TaskCreatorAgent

logger = logging.getLogger(__name__)

TaskConstants = TaskCreatorConstants

def generate_and_save_tasks(project_id: UUID, user_id: UUID):
    """
    Analyzes project requirements and technical documentation using TaskCreatorAgent 
     to generate and save actionable tasks.
    """
    db = SessionLocal()
    try:
        logger.info(f"Initiating agent-driven task generation for project ID: {project_id}")
        
        # 1. Fetch Necessary Documentation
        documents = db.query(Document).filter(
            Document.project_id == project_id,
            (Document.title.ilike("%Requirement%") | Document.title.ilike("%Technical%"))
        ).all()
        
        req_doc = next((d for d in documents if "requirement" in d.title.lower()), None)
        tech_doc = next((d for d in documents if "technical" in d.title.lower()), None)
        
        if not req_doc or not tech_doc:
            missing = []
            if not req_doc: missing.append("Requirements")
            if not tech_doc: missing.append("Technical")
            logger.warning(f"Missing {', '.join(missing)} documentation for project {project_id}. Skipping generation.")
            return

        def get_document_content(doc_id: UUID) -> str:
            blocks = db.query(DocumentBlock).filter(
                DocumentBlock.doc_id == doc_id
            ).order_by(DocumentBlock.position_key).all()
            return "\n".join([b.content for b in blocks if b.content]).strip()

        requirement_md = get_document_content(req_doc.id)
        technical_md = get_document_content(tech_doc.id)

        # 2. Run Task Creator Agent
        agent = TaskCreatorAgent(user_id=user_id, project_id=project_id)
        
        prompt_with_context = user_prompt.format(
            requirement_document=requirement_md,
            technical_document=technical_md
        )
        
        messages = [
            {"role": "user", "content": prompt_with_context}
        ]
        
        result = agent.run(messages)
        
        if result.get("tasks_saved"):
            logger.info(f"TaskCreatorAgent successfully generated and saved tasks for project {project_id}")
        else:
            logger.warning(f"TaskCreatorAgent finished but no tasks were saved for project {project_id}. Output: {result.get('content')}")

    except Exception as exc:
        logger.exception(f"Critical failure during agent-driven task generation for project {project_id}: {exc}")
    finally:
        db.close()
