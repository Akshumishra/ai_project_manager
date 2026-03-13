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

        logger.info(f"Executing SQL query for project_id: {project_id}")
        logger.info(f"SQL: {sql}")
        stripped = sql.strip().upper()
        if not stripped.startswith("SELECT"):
            logger.warning(f"Rejected non-SELECT query: {stripped}")
            return (
                "Error: Only SELECT statements are allowed. "
                "Your query was rejected for safety."
            )

        session = SessionLocal()
        try:
            # Set the project_id in the session for Row Level Security (RLS)
            # Use SET LOCAL to ensure it only persists for the current transaction
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
            columns = list(result.keys())

            if not rows:
                return "No results found."

            lines = [" | ".join(str(c) for c in columns)]
            lines.append("-" * len(lines[0]))
            for row in rows:
                lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))

            return "\n".join(lines)

        except Exception as exc:
            logger.error(f"Database error executing query: {exc}", exc_info=True)
            return f"Database error: {exc}"
        finally:
            session.close()


    return run_sql_query
