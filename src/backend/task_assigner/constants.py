from src.backend.constants import DefaultConstants

class TaskAssignerConstants(DefaultConstants):
    WORKFLOW_NAME = DefaultConstants.WF_TASK_ASSIGN
    REDIRECT_PATH = "/task-board"
    MODEL = "gpt-4.1-mini"
    AGENT_NAME = "Task Assigner Agent"
