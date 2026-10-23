from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["reader", "author", "admin"]

class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["reader", "author"] = "reader"

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)

class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class TagOut(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)

class CommentOut(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PostOut(BaseModel):
    id: int
    author_id: int
    title: str
    content: str
    cover_image_path: str | None
    status: str
    created_at: datetime
    published_at: datetime | None
    tags: list[str] = []
    approved_comments: list[CommentOut] = []

class PostPage(BaseModel):
    items: list[PostOut]
    page: int
    limit: int
    total: int

class PostStats(BaseModel):
    post_id: int
    title: str
    status: str
    total_comments: int
    approved_comments: int
