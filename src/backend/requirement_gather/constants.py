from src.backend.constants import DefaultConstants

class RequirementAgentConstants(DefaultConstants):
    MODEL = "gpt-5-mini"
    TEMPERATURE = 0.2
    WORKFLOW_NAME = "requirement_gathering"
    REDIRECT_PATH = "/tech-doc"
    REQ_DOC_LABEL = "Requirements"
