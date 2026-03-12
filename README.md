# AI Project Manager

This project is an AI-powered project manager assistant embedded in Slack, designed to help teams manage tasks, documents, and project context efficiently.

## Row Level Security (RLS) for Project Isolation

This project implements PostgreSQL Row Level Security (RLS) to ensure that the AI agent can only access data belonging to the current `project_id`. This provides a hard security boundary at the database level, preventing data leakage between different projects.

### Overview

Every query executed by the AI agent is scoped using a session-level configuration variable `app.project_id`. The database uses this variable to automatically filter results for all supported tables.

### Migration Instructions

#### Prerequisites
- Database user with `SUPERUSER` or `BYPASSRLS` privileges.

#### Running the Migration
Apply the RLS configuration by running the migration script:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 src/backend/scripts/enable_rls.py
```

This script:
1. Enables RLS on all relevant tables.
2. Forces RLS even for table owners (for maximum security).
3. Creates idempotent policies named `project_isolation_<table_name>`.

### Technical Details

#### Session Management
The AI agent sets the project context before executing any SQL query within a transaction:

```sql
SET LOCAL app.project_id = 'your-project-uuid';
```

Using `SET LOCAL` within a transaction ensures:
- The scope is strictly limited to the current request.
- The variable does not leak between pooled database connections.

#### Implementation in Code
The session variable is set automatically in `src/backend/qa_chatbot/qa_agent/tools/run_sql_query.py` before the LLM-generated query is executed.

#### Covered Tables

- `projects`
- `project_slack_details`
- `project_members`
- `tasks`
- `documents`
- `document_blocks` (indirectly via `doc_id` join)
- `requirement_chats` (direct isolation via `project_id`)

### Verification

#### Automated Status Check
Confirm that RLS is enabled and policies are active:

```bash
python3 src/backend/scripts/check_rls_status.py
```

#### Manual Confirmation
You can verify the scoping by executing a test query from a Slack channel and confirming the results are correctly restricted to that project's data.

---

## How to Run The Application

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   Create a `.env` file based on `.env.sample`.

3. **Start the FastAPI Server**:
   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   python3 main.py
   ```