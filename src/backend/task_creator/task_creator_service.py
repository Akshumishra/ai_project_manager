from datetime import datetime, timezone
import json
import logging
from uuid import UUID
from sqlalchemy.orm import Session
from src.backend.db.database import SessionLocal

from src.backend.model.task import Task, TaskCategory, TaskPriority, TaskStatus, TaskComplexity
from src.backend.model.document import Document, DocumentBlock
from src.backend.config import settings
from src.backend.task_creator.constants import TaskCreatorConstants
from src.backend.task_creator.task_creator_agent.prompt import (
    system_prompt,
    user_prompt
)
from .task_creator_agent.agent import TaskCreatorAgent
from src.backend.utils.workflow_utils import set_workflow_status

logger = logging.getLogger(__name__)

TaskConstants = TaskCreatorConstants


def generate_and_save_tasks(project_id: UUID, user_id: UUID):
    """
    Analyzes project requirements and technical documentation using TaskCreatorAgent
    to generate and save actionable tasks.
    Tracks workflow status so the frontend can poll for progress.
    """
    db = SessionLocal()
    try:
        logger.info(f"Initiating agent-driven task generation for project ID: {project_id}")

        # Mark as generating so the frontend can display a live status
        set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, "generating")

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
            set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, "failed_missing_docs")
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
            set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, "completed")
        else:
            content = result.get("content", "")
            try:
                # Fallback: If agent returned JSON but didn't call the tool
                stripped_content = content.strip()
                if stripped_content.startswith("[") and stripped_content.endswith("]"):
                    tasks_data = json.loads(stripped_content)
                    if isinstance(tasks_data, list) and len(tasks_data) > 0:
                        from src.backend.task_creator.task_creator_agent.tools.save_tasks import make_save_tasks_tool
                        save_tool = make_save_tasks_tool(user_id=user_id, project_id=project_id)
                        save_result = save_tool.run({"tasks": tasks_data})
                        logger.info(f"TaskCreatorAgent fallback: saved tasks from JSON content. Result: {save_result}")
                        set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, "completed")
                        return
            except Exception as e:
                logger.error(f"Fallback task parsing failed for project {project_id}: {e}")

            logger.warning(f"TaskCreatorAgent finished but no tasks were saved for project {project_id}. Output: {content[:200]}...")
            set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, "failed")

    except Exception as exc:
        logger.exception(f"Critical failure during agent-driven task generation for project {project_id}: {exc}")
        try:
            set_workflow_status(db, project_id, TaskConstants.WORKFLOW_NAME, "failed")
        except Exception:
            pass
    finally:
        db.close()
