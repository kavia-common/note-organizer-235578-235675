from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.api.db import get_db
from src.api.models import NoteTag, Tag, User
from src.api.schemas import TagCreateRequest, TagPublic, TagUpdateRequest

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[TagPublic],
    summary="List tags",
    description="List tags for the current user, optionally search by name prefix.",
)
def list_tags(
    q: str | None = Query(default=None, description="Optional search query for tag name."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TagPublic]:
    """List tags for current user."""
    query = db.query(Tag).filter(Tag.user_id == user.id)
    if q:
        query = query.filter(Tag.name.ilike(f"%{q}%"))
    tags = query.order_by(Tag.name.asc()).all()
    return [TagPublic.model_validate(t) for t in tags]


@router.post(
    "",
    response_model=TagPublic,
    status_code=201,
    summary="Create tag",
    description="Create a tag for the current user (unique per user by name).",
)
def create_tag(
    req: TagCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TagPublic:
    """Create a new tag."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty.")

    existing = db.query(Tag).filter(Tag.user_id == user.id, Tag.name == name).first()
    if existing:
        return TagPublic.model_validate(existing)

    tag = Tag(
        id=__import__("uuid").uuid4(),
        user_id=user.id,
        name=name,
        created_at=datetime.now(timezone.utc),
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagPublic.model_validate(tag)


@router.patch(
    "/{tag_id}",
    response_model=TagPublic,
    summary="Update tag",
    description="Rename a tag (must belong to current user).",
)
def update_tag(
    tag_id: UUID,
    req: TagUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TagPublic:
    """Update a tag name."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found.")

    new_name = req.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty.")

    conflict = db.query(Tag).filter(Tag.user_id == user.id, Tag.name == new_name, Tag.id != tag_id).first()
    if conflict:
        raise HTTPException(status_code=409, detail="A tag with that name already exists.")

    tag.name = new_name
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagPublic.model_validate(tag)


@router.delete(
    "/{tag_id}",
    status_code=204,
    summary="Delete tag",
    description="Delete a tag (must belong to current user). Detaches from notes via cascade in note_tags.",
)
def delete_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete a tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found.")

    # note_tags rows will cascade delete via FK
    db.query(NoteTag).filter(NoteTag.tag_id == tag_id).delete()
    db.delete(tag)
    db.commit()
    return None
