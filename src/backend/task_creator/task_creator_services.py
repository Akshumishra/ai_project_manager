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
from src.backend.config import Config
from src.backend.task_creator.task_creator_agent.prompt import (
    system_prompt,
    user_prompt
)

logger = logging.getLogger(__name__)

def generate_and_save_tasks(project_id: UUID):
    """
    Background service to analyze documentation and generate initial tasks (Internal Session).
    """
    db = SessionLocal()
    try:
        logger.info(f"Starting task generation for project: {project_id}")
        
        # 1. Fetch Project Documentation
        req_doc = db.query(Document).filter(
            Document.project_id == project_id,
            Document.title.ilike("%Requirement%")
        ).first()
        
        tech_doc = db.query(Document).filter(
            Document.project_id == project_id,
            Document.title.ilike("%Technical%")
        ).first()
        
        if not req_doc or not tech_doc:
            logger.warning(f"Missing documentation for project {project_id}. Task generation skipped.")
            return

        def get_md(doc_id):
            blocks = db.query(DocumentBlock).filter(DocumentBlock.doc_id == doc_id).order_by(DocumentBlock.position_key).all()
            return "\n".join([b.content for b in blocks if b.content])

        req_md = get_md(req_doc.id)
        tech_md = get_md(tech_doc.id)

        # 2. Call LLM
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            api_key=Config.OPENAI_API_KEY
        )
        
        formatted_user_prompt = user_prompt.format(
            requirement_document=req_md,
            technical_document=tech_md
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": formatted_user_prompt}
        ]
        
        response = llm.invoke(messages)
        content = str(response.content)
        
        # Clean JSON markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        generated_tasks = json.loads(content)

        # 3. Save Tasks
        for t_data in generated_tasks:
            # Map category
            cat_str = t_data.get("category", "Backend").lower()
            try:
                category = TaskCategory(cat_str)
            except ValueError:
                # Fallback mapping
                if "backend" in cat_str: category = TaskCategory.BACKEND
                elif "frontend" in cat_str: category = TaskCategory.FRONTEND
                elif "database" in cat_str: category = TaskCategory.DATABASE
                elif "ai" in cat_str: category = TaskCategory.AI_ML
                elif "devops" in cat_str: category = TaskCategory.DEVOPS
                elif "qa" in cat_str: category = TaskCategory.QA
                elif "security" in cat_str: category = TaskCategory.SECURITY
                else: category = TaskCategory.BACKEND
                
            # Map priority
            priority_str = t_data.get("priority", "Medium").lower()
            try:
                priority = TaskPriority(priority_str)
            except ValueError:
                priority = TaskPriority.MEDIUM

            # Map complexity
            sp = t_data.get("story_points", 3)
            if sp <= 3: complexity = TaskComplexity.LOW
            elif sp <= 8: complexity = TaskComplexity.MEDIUM
            else: complexity = TaskComplexity.HIGH

            new_task = Task(
                title=t_data["title"],
                description=t_data.get("description"), # Already contains markdown + criteria
                project_id=project_id,
                category=category,
                priority=priority,
                complexity=complexity,
                story_points=sp,
                estimated_hours=t_data.get("estimated_hours"),
                ai_generated=True,
                status=TaskStatus.TODO,
                project_member_id=None # Initially unassigned
            )
            db.add(new_task)
        
        db.commit()
        logger.info(f"Successfully generated {len(generated_tasks)} tasks for project {project_id}")

    except Exception as e:
        logger.exception(f"Error in task generation: {e}")
        db.rollback()
