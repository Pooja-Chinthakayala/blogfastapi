from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_roles
from app.models import Tag, User
from app.schemas import TagCreate, TagOut

router = APIRouter(prefix="/tags", tags=["Tags"])

@router.get("", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.scalars(select(Tag).order_by(Tag.name)).all()

@router.post("", response_model=TagOut, status_code=201)
def create_tag(data: TagCreate, db: Session = Depends(get_db),
               user: User = Depends(require_roles("admin"))):
    name = data.name.strip()
    if db.scalar(select(Tag).where(Tag.name == name)):
        raise HTTPException(status_code=409, detail="Tag already exists")
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag
