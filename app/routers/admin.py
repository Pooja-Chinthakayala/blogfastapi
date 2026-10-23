from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_roles
from app.models import Comment, Post, User

router = APIRouter(prefix="/admin", tags=["Administration"])

def get_comment(comment_id: int, db: Session) -> Comment:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

@router.patch("/comments/{comment_id}/approve")
def approve_comment(comment_id: int, db: Session = Depends(get_db),
                    admin: User = Depends(require_roles("admin"))):
    comment = get_comment(comment_id, db)
    if comment.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending comments can be approved")
    comment.status = "approved"
    db.commit()
    return {"message": "Comment approved", "comment_id": comment.id, "status": comment.status}

@router.patch("/comments/{comment_id}/reject")
def reject_comment(comment_id: int, db: Session = Depends(get_db),
                   admin: User = Depends(require_roles("admin"))):
    comment = get_comment(comment_id, db)
    if comment.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending comments can be rejected")
    comment.status = "rejected"
    db.commit()
    return {"message": "Comment rejected", "comment_id": comment.id, "status": comment.status}

@router.get("/posts")
def admin_list_all_posts(db: Session = Depends(get_db),
                         admin: User = Depends(require_roles("admin"))):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    return [{"id": p.id, "title": p.title, "status": p.status, "author_id": p.author_id}
            for p in posts]

@router.get("/comments/pending")
def pending_comments(db: Session = Depends(get_db),
                     admin: User = Depends(require_roles("admin"))):
    comments = db.query(Comment).filter(Comment.status == "pending").order_by(Comment.created_at).all()
    return [{"id": c.id, "post_id": c.post_id, "author_id": c.author_id,
             "content": c.content, "status": c.status, "created_at": c.created_at}
            for c in comments]
