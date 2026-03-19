# 🤖 AI Project Manager

A full-stack AI-powered project management tool that automates requirement gathering, technical documentation, and task creation using LLM agents.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Setup — Backend](#setup--backend)
- [Setup — Frontend](#setup--frontend)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [External Services Required](#external-services-required)

---

## 🏗 Architecture Overview

```
ai-project-manager/
├── src/
│   ├── backend/          # FastAPI Python backend
│   │   ├── auth/         # JWT authentication
│   │   ├── project/      # Project & member management
│   │   ├── requirement_gather/  # Requirement agent (LLM)
│   │   ├── technical_doc/       # Tech doc agent (LLM)
│   │   ├── task_creator/        # Auto task generation (LLM)
│   │   ├── collaborative_document/  # Real-time editor (WebSocket + Redis)
│   │   ├── resume_parsing/      # Resume upload & parsing
│   │   ├── model/               # SQLAlchemy DB models
│   │   └── main.py              # FastAPI app entry point
│   └── frontend/         # React + Vite frontend
│       └── src/
│           ├── pages/    # Route pages
│           ├── components/  # UI components
│           ├── hooks/    # Custom React hooks
│           └── api.js    # Axios API layer
├── requirements.txt      # Python dependencies
└── .env.sample           # Environment variable template
```

**Tech Stack:**
| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Axios, Marked |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL |
| Cache / Real-time | Redis |
| AI | OpenAI GPT-4o / GPT-4o-mini via LangChain |
| Auth | JWT (access + refresh tokens) |
| Email | Brevo (SMTP) |

---

## ✅ Prerequisites

Make sure the following are installed on your machine:

| Tool           | Version | Install                                  |
| -------------- | ------- | ---------------------------------------- |
| **Python**     | 3.11+   | [python.org](https://python.org)         |
| **Node.js**    | 18+     | [nodejs.org](https://nodejs.org)         |
| **PostgreSQL** | 14+     | [postgresql.org](https://postgresql.org) |
| **Redis**      | 7+      | [redis.io](https://redis.io)             |
| **Git**        | Any     | [git-scm.com](https://git-scm.com)       |

---

## ⚙️ Setup — Backend

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd ai-project-manager
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the PostgreSQL database

```bash
psql -U postgres
CREATE DATABASE ai_project_manager;
\q
```

> You can use any database name — just update `DATABASE_URL` in your `.env` accordingly.

### 5. Set up environment variables

```bash
cp .env.sample .env
```

Open `.env` and fill in all the required values (see [Environment Variables](#environment-variables) below).

### 6. Start Redis

Make sure Redis is running locally on the default port `6379`:

```bash
redis-server
# or on macOS with Homebrew:
brew services start redis
```

---

## ⚙️ Setup — Frontend

```bash
cd src/frontend
npm install
```

Create a `.env` file in `src/frontend/` (optional — only if your backend is not on port 8000):

```bash
# src/frontend/.env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🔑 Environment Variables

Copy `.env.sample` to `.env` in the project root and fill in the values:

```env
# ── Database ─────────────────────────────────────────────
DATABASE_URL=postgresql://postgres:yourpassword@localhost/ai_project_manager

# ── OpenAI ───────────────────────────────────────────────
OPENAI_API_KEY=sk-...

# ── JWT Auth ─────────────────────────────────────────────
ACCESS_SECRET_KEY=<generate a long random string>
REFRESH_SECRET_KEY=<generate a different long random string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Frontend URLs ─────────────────────────────────────────
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:5174"]

# ── Email (Brevo SMTP) — Optional ─────────────────────────
BREVO_API_KEY=
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
EMAILS_FROM=your@email.com

# ── Slack — Optional ──────────────────────────────────────
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_REDIRECT_URI=http://localhost:8000/auth/slack/callback
```

**To generate secure secret keys:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 🚀 Running the Application

### Start the Backend

From the project root (with `.venv` active):

```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: **http://localhost:8000**  
Interactive API docs: **http://localhost:8000/docs**

> The database tables are created automatically on first startup — no migrations needed.

### Start the Frontend

In a separate terminal:

```bash
cd src/frontend
npm run dev
```

The app will be available at: **http://localhost:5173**

---

## 🌐 External Services Required

| Service          | Required    | Purpose                                                     |
| ---------------- | ----------- | ----------------------------------------------------------- |
| **OpenAI API**   | ✅ Required | LLM for requirement agent, tech doc agent, and task creator |
| **PostgreSQL**   | ✅ Required | Primary database                                            |
| **Redis**        | ✅ Required | Real-time collaborative document sync                       |
| **Brevo (SMTP)** | ⚠️ Optional | Email invitations and OTP verification                      |
| **Slack**        | ⚠️ Optional | Standup posting and notifications                           |

> If email or Slack keys are missing, those features will be silently disabled — the core app will still work.

---

## 🔄 Application Flow

1. **Register / Login** — Create an account or sign in
2. **Create a Project** — Start a new AI-managed project
3. **Requirement Agent** — Chat with the AI to define your project requirements; the spec is auto-saved to the canvas
4. **Tech Doc Agent** — Chat with the AI to build a technical specification; once saved, **task generation starts automatically**
5. **Tasks** — View AI-generated tasks; assign them to members or create manual ones
6. **Documents** — Use the collaborative real-time editor to write additional project documents
7. **Standups** — Log and track daily standups per project

---

## 🛠 Common Issues

| Issue                                      | Fix                                                                       |
| ------------------------------------------ | ------------------------------------------------------------------------- |
| `ModuleNotFoundError`                      | Make sure your virtual environment is active: `source .venv/bin/activate` |
| `could not connect to server` (PostgreSQL) | Ensure PostgreSQL is running and `DATABASE_URL` is correct                |
| Redis connection error                     | Run `redis-server` or `brew services start redis`                         |
| CORS errors                                | Check that your frontend URL is in the `ALLOWED_ORIGINS` list in `.env`   |
| OpenAI API errors                          | Verify your `OPENAI_API_KEY` is valid and has sufficient credits          |

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
