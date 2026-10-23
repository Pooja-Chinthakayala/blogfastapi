from tests.conftest import register_user, token_for, auth_headers

def test_comment_hidden_until_admin_approval(client):
    register_user(client, "Author", "author@example.com", role="author")
    register_user(client, "Reader", "reader@example.com")
    register_user(client, "Admin", "admin@example.com", role="reader")
    # Public registration intentionally cannot create admins; promote only in test DB.
    from app.database import SessionLocal
    from app.models import User
    db = SessionLocal()
    admin_user = db.query(User).filter_by(email="admin@example.com").first()
    admin_user.role = "admin"
    db.commit()
    db.close()

    author_token = token_for(client, "author@example.com")
    reader_token = token_for(client, "reader@example.com")
    admin_token = token_for(client, "admin@example.com")
    post = client.post("/posts", json={"title": "Post", "content": "Body"},
                       headers=auth_headers(author_token)).json()
    client.patch(f"/posts/{post['id']}/publish", headers=auth_headers(author_token))
    comment = client.post(f"/posts/{post['id']}/comments", json={"content": "Nice post"},
                          headers=auth_headers(reader_token))
    assert comment.status_code == 201
    comment_id = comment.json()["id"]
    assert comment.json()["status"] == "pending"
    assert client.get(f"/posts/{post['id']}/comments").json() == []
    approved = client.patch(f"/admin/comments/{comment_id}/approve",
                            headers=auth_headers(admin_token))
    assert approved.status_code == 200
    visible = client.get(f"/posts/{post['id']}/comments").json()
    assert len(visible) == 1
    assert visible[0]["status"] == "approved"

def test_reader_cannot_approve_comment(client):
    register_user(client, "Reader", "reader@example.com")
    token = token_for(client, "reader@example.com")
    response = client.patch("/admin/comments/999/approve", headers=auth_headers(token))
    assert response.status_code == 403
