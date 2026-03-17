# AI Project Manager: Implemented Features Documentation

This document summarizes the technical features implemented in the Standup Management system to improve team momentum, context persistence, and reporting clarity.

## 1. Momentum Engine (Task Auto-Promotion)
To ensure the standup process always encourages progress, the system now includes an "auto-promotion" logic.
- **Functionality**: Before generating a standup prompt, the `promote_idle_todo_to_inprogress` method checks if any project member has zero active work (neither `INPROGRESS` nor `BLOCKED`).
- **Logic**: It identifies the user's `TODO` task with the nearest deadline and automatically moves it to `INPROGRESS`.
- **Impact**: This prevents "stale" standup messages where members appear to have no current focus, keeping the project moving without manual manager intervention.

## 2. Continuous Context (Summary Insights)
Context from previous discussions is now preserved across sessions.
- **Extraction**: The `_extract_summary_insights` method parses the *finalized summary* of the most recent standup.
- **Integration**: It extracts bullet points (excluding system artifacts like "Great job team!") and injects them into the *next morning's* standby prompt under "💡 Insights from Last Standup".
- **Impact**: This ensures that important decisions or updates mentioned in a summary are not forgotten the next day.

## 3. Persistent "New Task" Tracking
Tasks created during a standup session are now highlighted in the subsequent initiation.
- **Tracking**: When a member adds a task via the bot, it's captured in the action logs.
- **Highlights**: The system tracks these "newly created" tasks and displays them in the next prompt under "🆕 Tasks Added Last Standup".
- **Impact**: Improves team awareness of scope changes and new assignments immediately.

## 4. Smart Blocker Management & Validation
The system now filters out low-value or redundant blocker information.
- **Reason Validation**: `_is_meaningful_blocker_reason` filters out entries like "N/A", "None", "Unknown", or default responses where the AI couldn't find a specific reason.
- **Blocked By Filtering**: `_should_show_blocked_by` hides "Blocked By: self" or "Blocked By: me" to reduce noise.
- **Ghost Blocker Removal**: If a project has no tasks currently in `BLOCKED` status, the "Member Blockers" section is entirely omitted from the prompt to avoid confusing developers with stale data.

## 5. Enhanced Task Visibility ("Next Up")
For members without active work, the bot provides a forward-looking view.
- **Next Up Section**: If a user has no `INPROGRESS` tasks, the bot displays a "Next Up" list containing their `TODO` tasks, sorted by deadline.
- **Impact**: Provides immediate direction for members who just finished their work.

## 6. Automated Metadata for AI-Created Tasks
Ensures all tasks created via natural language have the necessary database fields.
- **Default Deadlines**: If the user or AI doesn't specify a deadline for a new task, the system automatically assigns a default deadline of **7 days** from creation.
- **Logging**: All auto-assignments and status changes are recorded in the `TaskLog` for auditability.

## 7. UI/UX Polishing
- **Artifact Removal**: Implemented `_strip_to_self` to remove internal tracking artifacts like "to self" from Slack summaries and insights, keeping the team-facing messages clean.
- **Prompt Integrity**: Updated the LLM "Refine Prompt" instructions to strictly protect new data-driven sections (Insights, Overdue Tasks), preventing the AI from hallucinating or removing critical data.
- **Slack API Robustness**: Added a fallback mechanism that uses `conversations.history` if the standard `replies` API fails to return threaded messages.
