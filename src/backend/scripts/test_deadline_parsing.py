from dateutil import parser
from datetime import datetime

test_cases = [
    "by Friday",
    "next Monday",
    "by 20th March",
    "tomorrow",
    "next week"
]

print(f"Current Time: {datetime.now()}")
for tc in test_cases:
    try:
        dt = parser.parse(tc, fuzzy=True)
        print(f"Input: '{tc}' -> Parsed: {dt}")
    except Exception as e:
        print(f"Input: '{tc}' -> Error: {e}")
