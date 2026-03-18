PROMPT_TEMPLATE = """
You are an expert resume parser.

Extract the following fields from the resume:

1. skills (List of strings)
2. yoe (Total years of experience as an integer)
3. designation (String)

Rules:
- Return ONLY valid JSON
- Use the following schema: {{"skills": [], "yoe": 0, "designation": ""}}
- Do not include explanations
- If information is missing return empty values (0 for yoe)

Resume:
{resume}
"""