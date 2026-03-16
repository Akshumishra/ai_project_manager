from langchain_core.tools import tool
from sqlalchemy import text
from src.backend.db.database import SessionLocal
from src.backend.config import Config
from src.backend.logger import get_logger

logger = get_logger("sql_tool")

def make_run_sql_query_tool(project_id: str, slack_user_id: str, project_member_id: str):
   
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
        
        # 1. Basic Safety Checks
        stripped = sql.strip()
        upper_stripped = stripped.upper()
        
        if not upper_stripped.startswith("SELECT"):
            logger.warning(f"Rejected non-SELECT query: {upper_stripped}")
            return "Error: Only SELECT statements are allowed."

        # Prevent multi-statement queries
        if ";" in stripped[:-1] and any(c.isalnum() for c in stripped[stripped.find(";")+1:]):
             logger.warning(f"Rejected multi-statement query: {stripped}")
             return "Error: Multi-statement queries are not allowed for safety."

        # 2. Define strict allowlist (matching prompt documentation)
        SAFE_COLUMNS = {
            # Table columns
            "id", "name", "email", "slack_id", "created_at", "updated_at",
            "user_id", "skills", "experience", "designation",
            "project_id", "description", "status", "created_by",
            "workspace_id", "channel_id",
            "doc_id", "title", "content", "position_key", "type",
            "complexity", "deadline", "project_member_id", "role",
            "label", "category", "priority", "story_points", "estimated_hours",
            # Common aliases / aggregates
            "total_tasks", "assigned_to", "count", "num_tasks"
        }

        session = SessionLocal()
        try:
            # Set the project_id in the session for Row Level Security (RLS)
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

            # 3. Filter columns against allowlist
            safe_indices = [i for i, col in enumerate(all_columns) if col.lower() in SAFE_COLUMNS]
            filtered_columns = [all_columns[i] for i in safe_indices]

            if not filtered_columns:
                return "Error: No authorized columns were selected or query returned no data."

            if not rows:
                return "No results found."

            lines = [" | ".join(str(c) for c in filtered_columns)]
            lines.append("-" * len(lines[0]))
            
            for row in rows:
                # Only include values for safe columns
                safe_values = [row[i] for i in safe_indices]
                lines.append(" | ".join(str(v) if v is not None else "NULL" for v in safe_values))

            return "\n".join(lines)

        except Exception as exc:
            logger.error(f"Database error executing query: {exc}", exc_info=True)
            return f"Database error: {exc}"
        finally:
            session.close()


    return run_sql_query
