from pydantic import ValidationError
from src.backend.auth.schemas import UserDetailUpdate

try:
    data = {"skills": ["Python"], "yoe": 5, "designation": "Intern"}
    print(UserDetailUpdate(**data))
except ValidationError as e:
    print(e.errors())

try:
    data = {"skills": ["Python"], "yoe": "5", "designation": "Intern"}
    print(UserDetailUpdate(**data))
except ValidationError as e:
    print(e.errors())
