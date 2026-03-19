"""Consolidated initial migration

Revision ID: 3c3f0d1b07d6
Revises: 
Create Date: 2026-03-18 01:09:18.365035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c3f0d1b07d6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ENUM TYPES ---
    task_status_enum = sa.Enum(
        "todo", "in_progress", "completed", "blocked",
        name="task_status_enum"
    )
    task_priority_enum = sa.Enum(
        "high", "medium", "low",
        name="task_priority_enum"
    )
    task_complexity_enum = sa.Enum(
        "low", "medium", "high",
        name="task_complexity_enum"
    )
    task_category_enum = sa.Enum(
        "backend", "frontend", "database", "ai_ml",
        "devops", "qa", "security",
        name="task_category_enum"
    )

    task_status_enum.create(op.get_bind(), checkfirst=True)
    task_priority_enum.create(op.get_bind(), checkfirst=True)
    task_complexity_enum.create(op.get_bind(), checkfirst=True)
    task_category_enum.create(op.get_bind(), checkfirst=True)

    # --- TABLE CREATION ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),

        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("label", sa.Integer(), nullable=False),

        sa.Column("category", task_category_enum, nullable=False),
        sa.Column("priority", task_priority_enum, nullable=False, server_default="medium"),
        sa.Column("complexity", task_complexity_enum, nullable=False, server_default="medium"),
        sa.Column("status", task_status_enum, nullable=False, server_default="todo"),

        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("project_member_id", sa.UUID(), nullable=True),

        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_member_id"], ["project_members.id"]),
    )

    # --- INDEXES ---
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_project_member_id", "tasks", ["project_member_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_project_member_id", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")

    op.drop_table("tasks")

    sa.Enum(name="task_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="task_priority_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="task_complexity_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="task_category_enum").drop(op.get_bind(), checkfirst=True)
