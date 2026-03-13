"""
Meeting Bot — Module 4: Intelligent Meeting Management & Auto Documentation.

Entry point for the meeting_bot package. Exposes the primary public API
so callers can do:

    from meeting_bot import SessionManager
"""

from meeting_bot.bot.orchestrator import MultiSessionOrchestrator  # noqa: F401
from meeting_bot.bot.session_manager import SessionManager  # noqa: F401

__all__ = ["SessionManager", "MultiSessionOrchestrator"]
