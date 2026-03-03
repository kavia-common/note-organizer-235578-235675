from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer').")


class UserPublic(BaseModel):
    id: UUID = Field(..., description="User ID.")
    email: str = Field(..., description="User email.")
    display_name: Optional[str] = Field(default=None, description="Optional display name.")

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email (unique).")
    password: str = Field(..., min_length=6, description="User password (min 6 chars).")
    display_name: Optional[str] = Field(default=None, description="Optional display name.")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email.")
    password: str = Field(..., description="User password.")


class NoteCreateRequest(BaseModel):
    title: str = Field(default="", description="Note title.")
    content: str = Field(default="", description="Note body content.")
    is_pinned: bool = Field(default=False, description="Whether note is pinned.")
    is_favorited: bool = Field(default=False, description="Whether note is favorited.")


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="Updated title.")
    content: Optional[str] = Field(default=None, description="Updated content.")
    is_pinned: Optional[bool] = Field(default=None, description="Updated pinned flag.")
    is_favorited: Optional[bool] = Field(default=None, description="Updated favorited flag.")


class TagPublic(BaseModel):
    id: UUID = Field(..., description="Tag ID.")
    name: str = Field(..., description="Tag name.")

    class Config:
        from_attributes = True


class NotePublic(BaseModel):
    id: UUID = Field(..., description="Note ID.")
    title: str = Field(..., description="Note title.")
    content: str = Field(..., description="Note content.")
    is_pinned: bool = Field(..., description="Pinned flag.")
    is_favorited: bool = Field(..., description="Favorited flag.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")
    tags: List[TagPublic] = Field(default_factory=list, description="Tags attached to this note.")

    class Config:
        from_attributes = True


class NotesListResponse(BaseModel):
    items: List[NotePublic] = Field(..., description="List of notes.")
    total: int = Field(..., description="Total number of matched notes.")


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="New tag name.")


class TagUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="Updated tag name.")
