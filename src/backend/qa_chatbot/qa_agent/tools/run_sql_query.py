from typing import List, Tuple, Any, Optional
from langchain_core.tools import tool
from sqlalchemy import text
from src.backend.db.database import SessionLocal
from src.backend.config import settings
from src.backend.qa_chatbot.constants import QAAgentConstants
from src.backend.logger import get_logger

logger = get_logger("sql_tool")

def _validate_sql_safety(sql: str) -> Optional[str]:
    """Basic safety checks to ensure only SELECT queries are run."""
    stripped = sql.strip()
    upper_stripped = stripped.upper()
    
    if not upper_stripped.startswith("SELECT"):
        logger.warning(f"Rejected non-SELECT query: {upper_stripped}")
        return "Error: Only SELECT statements are allowed."

    if ";" in stripped[:-1] and any(c.isalnum() for c in stripped[stripped.find(";")+1:]):
         logger.warning(f"Rejected multi-statement query: {stripped}")
         return "Error: Multi-statement queries are not allowed for safety."
         
    return None

def _get_safe_columns_and_indices(all_columns: List[str]) -> Tuple[List[str], List[int]]:
    """Filters result columns against a strict allowlist."""
    safe_indices = [i for i, col in enumerate(all_columns) if col.lower() in QAAgentConstants.SAFE_COLUMNS]
    filtered_columns = [all_columns[i] for i in safe_indices]
    return filtered_columns, safe_indices

def _format_results_table(columns: List[str], rows: List[Any], safe_indices: List[int]) -> str:
    """Formats rows as a simple ASCII-like table."""
    if not columns:
        return "Error: No authorized columns were selected or query returned no data."

    if not rows:
        return "No results found."

    lines = [" | ".join(str(c) for c in columns)]
    lines.append("-" * len(lines[0]))
    
    for row in rows:
        safe_values = [row[i] for i in safe_indices]
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in safe_values))

    return "\n".join(lines)


def create_sql_query_tool(project_id: str, slack_user_id: str, project_member_id: str):
    
    @tool
    def run_sql_query(sql: str) -> str:
        """
        Execute a read-only SELECT query against the project database and
        return the results as a plain-text table.

        Only use this tool when you need data from the database.
        The query MUST be a SELECT statement — no INSERT / UPDATE / DELETE / DROP.
        Always filter tasks and documents by the literal `:project_id` bind parameter 
        provided automatically.

        Args:
            sql: A valid PostgreSQL SELECT statement using `:project_id` and `:project_member_id` placeholders.

        Returns:
            Query results as a formatted string, or an error message.
        """
        logger.debug(f"Executing SQL query for project_id: {project_id}")
        logger.debug(f"SQL: {sql}")
        
        error_msg = _validate_sql_safety(sql)
        if error_msg:
            return error_msg

        session = SessionLocal()
        try:
            session.execute(
                text("SET LOCAL app.project_id = :project_id"),
                {"project_id": project_id}
            )

            params = {
                "project_id": project_id,
                "slack_user_id": slack_user_id,
                "project_member_id": project_member_id
            }
            result = session.execute(text(sql), params)
            rows = result.fetchall()
            all_columns = list(result.keys())

            filtered_columns, safe_indices = _get_safe_columns_and_indices(all_columns)

            return _format_results_table(filtered_columns, rows, safe_indices)

        except Exception as exc:
            logger.error(f"Database error executing query: {exc}", exc_info=True)
            return f"Database error: {exc}"
        finally:
            session.close()

    return run_sql_query
