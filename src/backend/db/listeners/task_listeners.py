from sqlalchemy import func
from sqlalchemy.orm import object_session

def set_next_label(mapper, connection, target):
    """
    Automatically sets the next sequential label for a project before inserting a new task.
    This ensures that labels are always sequential per project, regardless of how they are created.
    """
    if target.label is not None and target.label > 0:
        return

    from src.backend.model.task import Task
    table = Task.__table__
    query = table.select().with_only_columns(func.max(table.c.label)).where(table.c.project_id == target.project_id)
    
    db_max = connection.execute(query).scalar() or 0
    
    session = object_session(target)
    session_max = 0
    if session:
        from src.backend.model.task import Task
        for obj in session.new:
            if isinstance(obj, Task) and obj.project_id == target.project_id and obj != target:
                if obj.label and obj.label > session_max:
                    session_max = obj.label
    
    target.label = max(db_max, session_max) + 1
