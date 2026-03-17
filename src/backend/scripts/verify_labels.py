
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.config import Config
from src.backend.model.task import Task, TaskStatus
from src.backend.model.project import Project
from src.backend.model.task_log import TaskLog

# Add project root to sys.path
sys.path.append(os.getcwd())

def verify_labels():
    print("🧪 Verifying Sequential Project-Specific Labels...")
    
    # Use owner URL to bypass RLS
    database_url = Config.STANDUP_DATABASE_URL.replace("standup_user", "postgres")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get two distinct projects
        projects = db.query(Project).limit(2).all()
        if len(projects) < 2:
            print("⚠️ Need at least two projects in the DB to verify isolation. Skipping isolation test.")
            p1 = projects[0]
            p2 = None
        else:
            p1 = projects[0]
            p2 = projects[1]
            print(f"Using Projects: {p1.name} and {p2.name}")

        # Cleanup existing test tasks
        db.query(TaskLog).filter(Task.title.like("Label Test:%")).filter(TaskLog.task_id == Task.id).delete(synchronize_session=False)
        db.query(Task).filter(Task.title.like("Label Test:%")).delete(synchronize_session=False)
        db.commit()

        # Get initial max labels
        p1_start = db.query(Task).filter(Task.project_id == p1.id).count()
        print(f"Project '{p1.name}' starting count: {p1_start}")
        
        # 1. Test Project 1 Sequence
        t1 = Task(project_id=p1.id, title="Label Test: P1-Task 1")
        t2 = Task(project_id=p1.id, title="Label Test: P1-Task 2")
        db.add_all([t1, t2])
        db.commit()
        
        db.refresh(t1)
        db.refresh(t2)
        
        print(f"P1-Task 1 Label: {t1.label}")
        print(f"P1-Task 2 Label: {t2.label}")
        
        if t2.label == t1.label + 1:
            print("✅ SUCCESS: Project 1 sequence is sequential.")
        else:
            print(f"❌ FAILURE: Project 1 sequence: {t1.label}, {t2.label}")

        # 2. Test Project 2 Isolation (if available)
        if p2:
            t3 = Task(project_id=p2.id, title="Label Test: P2-Task 1")
            db.add(t3)
            db.commit()
            db.refresh(t3)
            
            p2_new_label = t3.label
            print(f"P2-Task 1 Label: {p2_new_label}")
            
            # Check if it follows the p2 sequence, not p1
            # We can't know the exact starting label for p2 without checking, but it should be max(p2)+1
            if p2_new_label != t2.label + 1:
                print("✅ SUCCESS: Project 2 label is isolated from Project 1 sequence.")
            else:
                # This could happen by chance if p2's max was coincidentally one less than p1's next
                print("ℹ️ Project 2 label matched P1 next label (could be coincidental). Checking specific P2 max...")
                # Add another to P1 to be sure
                t4 = Task(project_id=p1.id, title="Label Test: P1-Task 3")
                db.add(t4)
                db.commit()
                db.refresh(t4)
                print(f"P1-Task 3 Label: {t4.label}")
                if t4.label == t2.label + 1:
                    print("✅ SUCCESS: Project 1 continues its own sequence.")
                else:
                    print(f"❌ FAILURE: Project 1 sequence broken: {t2.label} -> {t4.label}")

        # 3. Test Manual Label Override (should be respected)
        t_manual = Task(project_id=p1.id, title="Label Test: Manual", label=999)
        db.add(t_manual)
        db.commit()
        db.refresh(t_manual)
        print(f"Manual Task Label: {t_manual.label}")
        if t_manual.label == 999:
            print("✅ SUCCESS: Manual label override respected.")
        else:
            print(f"❌ FAILURE: Manual label reset to {t_manual.label}")

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    verify_labels()
