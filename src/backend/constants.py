class DefaultConstants:
    REQ_DOC_LABEL = "Requirement Specification"
    TECH_DOC_LABEL = "Technical Specification"

    WF_REQUIREMENT = "requirement_gathering"
    WF_TECH_DOC = "tech_doc_gathering"
    WF_TASK_GEN = "task_generation"
    WF_TASK_ASSIGN = "task_assignment"

    REDIRECT_PATH = "/project"
    TEMPERATURE = 0.0

    MODEL_CONFIG = {
        "gpt-4.1-mini": {"supports_temperature": True},
        "gpt-4.1-nano": {"supports_temperature": True},
        "gpt-5-mini": {"supports_temperature": False}
    }