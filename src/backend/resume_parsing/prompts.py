PROMPT_TEMPLATE = """
You are an expert resume parser.

Extract the following fields from the resume:

1. skills
2. experience_years
3. designation

Rules:
- Return ONLY valid JSON
- Do not include explanations
- If information is missing return empty values

Resume:
{resume}
"""
