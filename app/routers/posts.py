from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Comment, Post, PostTag, Tag, User
from app.schemas import CommentCreate, CommentOut, PostCreate, PostOut, PostPage, PostStats, PostUpdate

router = APIRouter(tags=["Posts"])

def to_post_out(post: Post, db: Session, include_comments: bool = True) -> PostOut:
    tag_names = db.scalars(select(Tag.name).join(PostTag, PostTag.tag_id == Tag.id)
                           .where(PostTag.post_id == post.id)).all()
    comments = []
    if include_comments:
        comments = db.scalars(select(Comment).where(
            Comment.post_id == post.id, Comment.status == "approved"
        ).order_by(Comment.created_at.desc())).all()
    return PostOut(id=post.id, author_id=post.author_id, title=post.title, content=post.content,
                   cover_image_path=post.cover_image_path, status=post.status,
                   created_at=post.created_at, published_at=post.published_at,
                   tags=list(tag_names), approved_comments=comments)

def get_post_or_404(post_id: int, db: Session) -> Post:
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

def ensure_owner_or_admin(post: Post, user: User):
    if user.role != "admin" and post.author_id != user.id:
        raise HTTPException(status_code=403, detail="You can only manage your own posts")

@router.get("/posts", response_model=PostPage)
def list_posts(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100),
               tag: str | None = None, db: Session = Depends(get_db)):
    query = select(Post).where(Post.status == "published")
    if tag:
        query = query.join(PostTag, PostTag.post_id == Post.id).join(Tag, Tag.id == PostTag.tag_id)
        query = query.where(func.lower(Tag.name) == tag.lower())
    total_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(total_query) or 0
    posts = db.scalars(query.order_by(Post.published_at.desc()).offset((page-1)*limit).limit(limit)).unique().all()
    return PostPage(items=[to_post_out(p, db) for p in posts], page=page, limit=limit, total=total)

@router.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = get_post_or_404(post_id, db)
    if post.status != "published":
        raise HTTPException(status_code=404, detail="Post not found")
    return to_post_out(post, db)

@router.post("/posts", response_model=PostOut, status_code=201)
def create_post(data: PostCreate, db: Session = Depends(get_db),
                user: User = Depends(require_roles("author"))):
    post = Post(author_id=user.id, title=data.title, content=data.content, status="draft")
    db.add(post)
    db.commit()
    db.refresh(post)
    return to_post_out(post, db)

@router.put("/posts/{post_id}", response_model=PostOut)
def update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db),
                user: User = Depends(require_roles("author"))):
    post = get_post_or_404(post_id, db)
    ensure_owner_or_admin(post, user)
    if post.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft posts can be edited")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return to_post_out(post, db)

@router.patch("/posts/{post_id}/publish", response_model=PostOut)
def publish_post(post_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_roles("author"))):
    post = get_post_or_404(post_id, db)
    ensure_owner_or_admin(post, user)
    if post.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft posts can be published")
    post.status = "published"
    post.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    return to_post_out(post, db)

@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    post = get_post_or_404(post_id, db)
    if user.role not in ("author", "admin"):
        raise HTTPException(status_code=403, detail="Only authors or admins can delete posts")
    ensure_owner_or_admin(post, user)
    db.delete(post)
    db.commit()
    return None

@router.post("/posts/{post_id}/cover", response_model=PostOut)
def upload_cover(post_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                 user: User = Depends(require_roles("author"))):
    post = get_post_or_404(post_id, db)
    ensure_owner_or_admin(post, user)
    if post.status != "draft":
        raise HTTPException(status_code=400, detail="Cover image can only be changed on a draft")
    allowed = {"image/jpeg": ".jpg", "image/png": ".png"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Only JPG and PNG images are allowed")
    content = file.file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 2 MB or smaller")
    # Check file signatures instead of trusting only the client-provided MIME type.
    valid = (file.content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")) or (
        file.content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
    if not valid:
        raise HTTPException(status_code=415, detail="File content does not match JPG/PNG type")
    folder = Path(settings.upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{allowed[file.content_type]}"
    destination = folder / filename
    destination.write_bytes(content)
    post.cover_image_path = str(destination)
    db.commit()
    db.refresh(post)
    return to_post_out(post, db)

@router.post("/posts/{post_id}/tags", response_model=PostOut)
def add_tags(post_id: int, tag_ids: list[int], db: Session = Depends(get_db),
             user: User = Depends(require_roles("author"))):
    post = get_post_or_404(post_id, db)
    ensure_owner_or_admin(post, user)
    if post.status != "draft":
        raise HTTPException(status_code=400, detail="Tags can only be changed on a draft")
    for tag_id in set(tag_ids):
        if not db.get(Tag, tag_id):
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
        exists = db.scalar(select(PostTag).where(PostTag.post_id == post.id, PostTag.tag_id == tag_id))
        if not exists:
            db.add(PostTag(post_id=post.id, tag_id=tag_id))
    db.commit()
    db.refresh(post)
    return to_post_out(post, db)

@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(post_id: int, data: CommentCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_roles("reader"))):
    post = get_post_or_404(post_id, db)
    if post.status != "published":
        raise HTTPException(status_code=404, detail="Post not found")
    comment = Comment(post_id=post.id, author_id=user.id, content=data.content, status="pending")
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    post = get_post_or_404(post_id, db)
    if post.status != "published":
        raise HTTPException(status_code=404, detail="Post not found")
    return db.scalars(select(Comment).where(Comment.post_id == post_id, Comment.status == "approved")
                      .order_by(Comment.created_at.desc())).all()

@router.get("/author/stats", response_model=list[PostStats])
def author_stats(db: Session = Depends(get_db), user: User = Depends(require_roles("author"))):
    posts = db.scalars(select(Post).where(Post.author_id == user.id)).all()
    result = []
    for post in posts:
        total = db.scalar(select(func.count(Comment.id)).where(Comment.post_id == post.id)) or 0
        approved = db.scalar(select(func.count(Comment.id)).where(
            Comment.post_id == post.id, Comment.status == "approved")) or 0
        result.append(PostStats(post_id=post.id, title=post.title, status=post.status,
                                total_comments=total, approved_comments=approved))
    return result
