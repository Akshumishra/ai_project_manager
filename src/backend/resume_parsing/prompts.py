PROMPT_TEMPLATE = """
You are an expert resume parser.

Extract the following fields from the resume text provided below:

1. skills: List of strings
2. yoe: Number (Total years of experience)
3. designation: Most recent job title

Rules:
- Return ONLY valid JSON
- Use the following schema: {{"skills": [], "yoe": 0, "designation": ""}}
- Do not include explanations
- If information is missing return null or empty list
"""
