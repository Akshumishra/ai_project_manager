import re
from typing import List, Dict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.backend.model.document import Document, DocumentBlock
from src.backend.model.project import Project


from src.backend.technical_doc.constants import TechDocAgentConstants

SECTION_HEADING_PREFIX = TechDocAgentConstants.SECTION_HEADING_PREFIX


def _normalize_heading(heading: str) -> str:
    return re.sub(r"\s+", " ", heading.strip().lower())


def _slugify_heading(heading: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", heading.strip().lower()).strip("_")
    return slug or "section"


def build_project_document_title(db: Session, project_id: UUID, document_label: str) -> str:
    project_title = db.query(Project.name).filter(Project.id == project_id).scalar()
    if not project_title:
        raise HTTPException(status_code=404, detail="Project not found")
    return f"{project_title} - {document_label}"


def split_markdown_sections(markdown: str) -> Dict[str, List[Dict[str, str]] | str]:
    lines = (markdown or "").splitlines()
    intro_lines: List[str] = []
    current_heading: str | None = None
    current_lines: List[str] = []
    sections: List[Dict[str, str]] = []

    def flush_section():
        if not current_heading:
            return
        sections.append(
            {
                "heading": current_heading,
                "content": "\n".join(current_lines).strip(),
            }
        )

    for line in lines:
        if line.startswith(SECTION_HEADING_PREFIX):
            flush_section()
            current_heading = line[len(SECTION_HEADING_PREFIX):].strip()
            current_lines = [line]
            continue

        if current_heading is None:
            intro_lines.append(line)
        else:
            current_lines.append(line)

    flush_section()

    return {
        "intro": "\n".join(intro_lines).strip(),
        "sections": sections,
    }


def build_markdown_from_sections(intro: str, sections: List[Dict[str, str]]) -> str:
    parts: List[str] = []

    if intro and intro.strip():
        parts.append(intro.strip())

    for section in sections:
        content = section["content"].strip()
        if content:
            parts.append(content)

    return "\n\n".join(parts).strip()


def replace_markdown_section(
    current_markdown: str | None,
    section_heading: str,
    section_markdown: str,
) -> str:
    if not current_markdown or not current_markdown.strip():
        return (section_markdown or "").strip()

    if not section_heading or not section_markdown or not section_markdown.strip():
        return current_markdown.strip()

    parsed = split_markdown_sections(current_markdown)
    sections = parsed["sections"]
    target_key = _normalize_heading(section_heading)
    replacement_section = {
        "heading": section_heading.strip(),
        "content": section_markdown.strip(),
    }

    replaced = False
    updated_sections: List[Dict[str, str]] = []
    for section in sections:
        if _normalize_heading(section["heading"]) == target_key:
            updated_sections.append(replacement_section)
            replaced = True
        else:
            updated_sections.append(section)

    if not replaced:
        updated_sections.append(replacement_section)

    return build_markdown_from_sections(parsed["intro"], updated_sections)


def merge_sectioned_markdown(current_markdown: str | None, updated_markdown: str | None) -> str:
    if not updated_markdown or not updated_markdown.strip():
        return (current_markdown or "").strip()

    if not current_markdown or not current_markdown.strip():
        return updated_markdown.strip()

    current_doc = split_markdown_sections(current_markdown)
    updated_doc = split_markdown_sections(updated_markdown)

    current_sections = current_doc["sections"]
    updated_sections = updated_doc["sections"]

    if not updated_sections:
        return updated_markdown.strip()

    updated_by_heading = {
        _normalize_heading(section["heading"]): section
        for section in updated_sections
    }

    merged_sections: List[Dict[str, str]] = []
    seen_headings = set()

    for current_section in current_sections:
        key = _normalize_heading(current_section["heading"])
        replacement = updated_by_heading.get(key, current_section)
        merged_sections.append(replacement)
        seen_headings.add(key)

    for updated_section in updated_sections:
        key = _normalize_heading(updated_section["heading"])
        if key not in seen_headings:
            merged_sections.append(updated_section)

    intro = updated_doc["intro"] or current_doc["intro"]
    return build_markdown_from_sections(intro, merged_sections)


def _delete_old_documents(db: Session, project_id: UUID, titles: List[str]):
    """Removes documents matching any of the provided titles."""
    old_docs = (
        db.query(Document)
        .filter(Document.project_id == project_id, Document.title.in_(titles))
        .all()
    )
    for old_doc in old_docs:
        db.delete(old_doc)
    if old_docs:
        db.flush()

def _create_document_blocks(db: Session, doc_id: UUID, user_id: UUID, markdown: str):
    """Parses markdown and saves it as individual document blocks."""
    parsed = split_markdown_sections(markdown)
    blocks_to_save: List[tuple[str, str, str]] = []

    intro = parsed["intro"]
    if intro:
        blocks_to_save.append(("0000_intro", "markdown", intro))

    for index, section in enumerate(parsed["sections"], start=1):
        position_key = f"{index:04d}_{_slugify_heading(section['heading'])}"
        blocks_to_save.append((position_key, "markdown", section["content"]))

    if not blocks_to_save:
        blocks_to_save.append(("0000_full_doc", "markdown", (markdown or "").strip()))

    for position_key, block_type, content in blocks_to_save:
        db.add(
            DocumentBlock(
                doc_id=doc_id,
                content=content,
                position_key=position_key,
                type=block_type,
                last_edited_by=user_id,
            )
        )

def save_markdown_as_section_blocks(
    db: Session,
    user_id: UUID,
    project_id: UUID,
    document_title: str,
    document_markdown: str,
    legacy_titles: List[str] | None = None,
) -> str:
    """Main service to orchestrate saving markdown content as sectioned document blocks."""
    try:
        title_candidates = [document_title]
        if legacy_titles:
            title_candidates.extend(legacy_titles)

        # 1. Cleanup
        _delete_old_documents(db, project_id, title_candidates)

        # 2. Create Document
        new_doc = Document(project_id=project_id, title=document_title, created_by=user_id)
        db.add(new_doc)
        db.flush()

        # 3. Create Blocks
        _create_document_blocks(db, new_doc.id, user_id, document_markdown)

        db.commit()
        return str(new_doc.id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
