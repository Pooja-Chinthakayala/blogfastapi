# Blog & Content Platform API

A FastAPI REST backend for authors, readers, and admins. Includes JWT authentication, role checks, draft/publish flow, tags, moderated comments, image uploads, pagination, author stats, tests, Alembic, and Docker.

## 1. Requirements
- Python 3.11+
- Docker (optional)
- PostgreSQL for Docker deployment; local default is SQLite for easy learning.

## 2. Local setup (SQLite)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs.

The app creates tables automatically for convenient local learning. For a migration-first workflow, remove the `Base.metadata.create_all` line from `app/main.py` and use Alembic.

## 3. Docker + PostgreSQL
```bash
docker compose up --build
```
Then open http://127.0.0.1:8000/docs. For any real deployment, replace the example database password and secret key.

## 4. Create the first admin
Public registration intentionally allows only `reader` or `author` roles to prevent users from registering themselves as admins. Register a user, then promote that user through a trusted database/admin provisioning process. Example for local SQLite:
```python
from app.database import SessionLocal
from app.models import User
db = SessionLocal()
user = db.query(User).filter_by(email="admin@example.com").first()
user.role = "admin"
db.commit()
db.close()
```
Never expose this promotion logic as a public endpoint.

## 5. API workflow
1. `POST /auth/register` with name, email, password, and optional role `reader` or `author`.
2. `POST /auth/login` with email/password; copy `access_token`.
3. In Swagger click **Authorize** and enter `Bearer <token>` if needed.
4. Author creates a draft with `POST /posts`.
5. Admin creates tags with `POST /tags`; add tag IDs to a draft using `POST /posts/{id}/tags` with a JSON array, e.g. `[1, 2]`.
6. Publish using `PATCH /posts/{id}/publish`.
7. Reader submits a comment. It remains pending until an admin approves it.
8. Public post/comment endpoints expose only published posts and approved comments.

## 6. Main endpoints
- Auth: `POST /auth/register`, `POST /auth/login`
- Posts: `GET /posts?page=1&limit=10&tag=python`, `GET /posts/{id}`, `POST /posts`, `PUT /posts/{id}`, `PATCH /posts/{id}/publish`, `DELETE /posts/{id}`, `POST /posts/{id}/cover`
- Tags: `GET /tags`, `POST /tags`, `POST /posts/{id}/tags`
- Comments: `POST /posts/{id}/comments`, `GET /posts/{id}/comments`, `DELETE /comments/{id}`
- Admin: `PATCH /admin/comments/{id}/approve`, `PATCH /admin/comments/{id}/reject`, `GET /admin/comments/pending`, `GET /admin/posts`
- Author stats: `GET /author/stats`

## 7. Tests
```bash
pytest -v
```

## 8. Alembic migrations
Initialize the migration directory if needed:
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
For a fresh migration-based setup, first remove automatic table creation in `app/main.py`. Review generated migrations before applying them.

## Security notes
- Change `SECRET_KEY` before deployment.
- Use HTTPS in production.
- Consider rate limiting login, account verification, malware scanning for uploaded files, and cloud object storage for production.
- Do not allow public role assignment to `admin`.
- The upload endpoint validates MIME, size, and basic file signatures; production systems should add image decoding/re-encoding and malware scanning.
