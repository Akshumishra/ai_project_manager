from src.backend.constants import DefaultConstants

class TechDocAgentConstants(DefaultConstants):
    MODEL = "gpt-4.1-mini"
    TEMPERATURE = 0.7
    WORKFLOW_NAME = "tech_doc_gathering"
    REQ_WORKFLOW_NAME = "requirement_gathering"
    TECH_DOC_LABEL = "Technical"
    REQ_DOC_LABEL = "Requirements"
    REDIRECT_PATH = "/"
    SECTION_HEADING_PREFIX = "## "
