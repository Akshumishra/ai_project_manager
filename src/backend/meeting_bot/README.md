# Google Meet Calendar Scheduler API (Fireflies-backed) 🚀

An API microservice designed to schedule Google Calendar meetings with auto-generated inside unlocked Google Meet links. Uses **Fireflies.ai** automations to capture transcripts seamlessly without local browser driver bot overheads, triggering automated GPT-4o analysis.

---

## 🛠 Features

- **Unlocked Meet Spaces**: Auto-generates calendar meetings with Meet links patched to `accessType='OPEN'` setting programmatically (bypasses room admission wall).
- **Auto-Join Trigger**: Includes `fred@fireflies.ai` on invite schedules to ensure continuous background transcript capture endpoints triggers safely.
- **Automated AI Analysis Pipeline**: Receives completed callback triggers securely via Fireflies GraphQL mapping to generate action items, risks, and narrative summaries.
- **Secure Handling**: No Fireflies secret variables stored directly inside script constants layouts triggers cleanly on central `pydantic` loading frames.

---

## 📦 Prerequisites

### 1. Python Environment
Fits standardized API layouts triggers framing:
```bash
pip install -r requirements.txt
```

### 2. Google OAuth Credentials
You must place your authorized Desktop or Web triggers client secrets file inside the workspace root directories:
*   `credentials.json` *(OAuth client secrets)*
*   `token.json` *(Generated securely on first run validation workflow trigger)*

---

## ⚙️ Configuration

Copy absolute configs layout parameters using the `.env.example` file wrapper rule layouts triggers safely fully:

```env
APP_ENVIRONMENT=development
GOOGLE_EMAIL=your@gmail.com
DATABASE_URL=postgresql://user:password@localhost:5432/db
REDIS_HOST=127.0.0.1
OPENAI_API_KEY=sk-...
FIREFLIES_API_KEY=...
```

---

## 🚀 Getting Started

### 1. Running as an API Service
Start the FastAPI trigger directly layout accurately:
```bash
PYTHONPATH=src/backend python3 -m src.backend.meeting_bot.main serve --port 8000
```
Visit `http://localhost:8000/docs` to see inside your interactive Swagger UI structures directly accurately.

---

## 📡 Core API Guidelines

### 🟢 `Sessions` Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/sessions/schedule-calendar` | Schedules Google Calendar meet, creates persistent Database frames, and returns unlocked Meet access framing setups. |

### 🔵 `Webhooks` Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/webhooks/fireflies/transcript` | Receives Fireflies callback payload, re-fetches securely on frames, and releases structured AI trigger analysis summary layouts. |

---

## 📂 Project Structure

```text
meeting_bot/
├── api/                # FastAPI logic (schemas, apps, routers)
│   ├── routers/
│   │   ├── sessions.py # Calendar allocation trigger maps
│   │   └── webhooks.py # Secure callback processor files
├── main.py             # CLI entrypoint serve triggers loading
```
