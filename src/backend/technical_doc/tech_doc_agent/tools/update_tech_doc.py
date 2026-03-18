from langchain_core.tools import tool

def make_update_tech_doc_tool():
    @tool
    def update_technical_document_draft(document_markdown: str):
        """
        Use this tool to output the latest drafted technical specification document in markdown format.
        Call this tool WHENEVER you create or modify the technical document so the user can see it on their screen.
        """
        return "Draft updated on user's screen."

    return [
        update_technical_document_draft
    ]
