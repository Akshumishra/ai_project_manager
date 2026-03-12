import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from sqlalchemy.orm import Session
from src.backend.db.database import SessionLocal, Base, engine
from src.backend.model.user import User
from src.backend.model.user_detail import UserDetail
import src.backend.model


def init_db():
    Base.metadata.create_all(bind=engine)

def insert_dummy_data():
    db: Session = SessionLocal()
    try:
        user1 = User(
            name="Akshita",
            email="akshita@example.com",
            password_hash="hashed_password_akshita"
        )
        db.add(user1)
        db.flush()

        detail1 = UserDetail(
            user_id=user1.id,
            skills="AI, LLM, Python, Backend",
            experience="AI Project Management",
            designation="AI Engineer",
            slack_id="U_AKSHITA"
        )
        db.add(detail1)

        user2 = User(
            name="Aarushi",
            email="aarushi@example.com",
            password_hash="hashed_password_aarushi"
        )
        db.add(user2)
        db.flush()

        detail2 = UserDetail(
            user_id=user2.id,
            skills="Frontend, React, UI/UX",
            experience="Frontend Development",
            designation="Frontend Developer",
            slack_id="U_AARUSHI"
        )
        db.add(detail2)

        user3 = User(
            name="Rudraksh",
            email="rudraksh@example.com",
            password_hash="hashed_password_rudraksh"
        )
        db.add(user3)
        db.flush()

        detail3 = UserDetail(
            user_id=user3.id,
            skills="DevOps, AWS, Testing",
            experience="DevOps and QA",
            designation="DevOps Engineer",
            slack_id="U_RUDRAKSH"
        )
        db.add(detail3)

        db.commit()
        print("Successfully inserted dummy data for Users and UserDetails.")

    except Exception as e:
        db.rollback()
        print(f"Failed to insert dummy data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    insert_dummy_data()
