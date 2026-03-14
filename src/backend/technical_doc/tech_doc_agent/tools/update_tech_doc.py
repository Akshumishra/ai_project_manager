from langchain_core.tools import tool

def make_update_tech_doc_tool():
    @tool
    def update_technical_document_draft(document_markdown: str):
        """
        Use this tool to output the latest drafted technical specification document in markdown format.
        Call this tool WHENEVER you create or modify the technical document so the user can see it on their screen.
        """
        return "Draft updated on user's screen."

    @tool
    def update_technical_document_section(section_heading: str, section_markdown: str):
        """
        Use this tool to update exactly one existing technical document section.
        Pass the section heading without the leading ##, and pass the full markdown
        for that section starting with the matching ## heading.
        """
        return f"Section {section_heading} updated on user's screen."

    return [
        update_technical_document_draft,
        update_technical_document_section,
    ]
