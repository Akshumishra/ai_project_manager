from fastapi import FastAPI
from app.routes import workspace_routes
from app.routes import channels
from app.routes import conversation_routes
from app.database import Base, engine

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(workspace_routes.router)
app.include_router(channels.router)
app.include_router(conversation_routes.router)

@app.get("/")
def root():
    return {"message": "Workspace API running"}