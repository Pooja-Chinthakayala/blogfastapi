from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.database import Base, engine
from app.routers import auth, posts, tags, admin, comments
from app import models  # noqa: F401 - registers SQLAlchemy models

app = FastAPI(title="Blog & Content Platform API", version="1.0.0",
              description="Role-based blogging API with draft/publish and moderated comments.")

# Convenience for local learning. In production, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(tags.router)
app.include_router(admin.router)
app.include_router(comments.router)

@app.get("/")
def root():
    return {"message": "Blog & Content Platform API", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}
print(settings.database_url) 
with engine.connect()as conn:
    print("connected to:",conn.exec_driver_sql("select database()").scalar())    
