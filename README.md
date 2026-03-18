# AI Project Manager - Backend

This service automates project management tasks, including daily Slack standups.

## 🚀 Getting Started

### 1. Environment Setup
Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration
Ensure `.env` has the following variables configured:
- `SLACK_BOT_TOKEN`: Token for your Slack App.
- `DATABASE_URL`: PostgreSQL connection string.
- `STANDUP_DATABASE_URL`: Connection string for the standup service.

### 3. Database Migrations
Ensure the database schema is up-to-date:
```bash
alembic upgrade head
```

### 4. Running the Application
The main entry point starts the FastAPI server and the **Standup Scheduler** automatically.
```bash
python src/backend/main.py
```

## ⏰ Standup Scheduler
The scheduler runs two daily jobs (Monday–Friday):
- **Morning Job (9:30 AM)**: Initiates standup prompts in configured Slack channels.
- **Evening Job (6:30 PM)**: Finalizes standups and posts summaries.

### Instantly Verify the Scheduler
To check if the morning and evening jobs are working without waiting for the scheduled time, run the verification script:
```bash
python src/backend/scripts/test_scheduler_jobs.py
```
This script manually triggers both jobs and provides logs to confirm success.