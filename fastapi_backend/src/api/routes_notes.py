from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.api.db import get_db
from src.api.models import Note, NoteTag, Tag, User
from src.api.schemas import NoteCreateRequest, NotePublic, NoteUpdateRequest, NotesListResponse, TagPublic

router = APIRouter(prefix="/notes", tags=["notes"])


def _note_to_public(db: Session, note: Note) -> NotePublic:
    tag_rows = (
        db.query(Tag)
        .join(NoteTag, NoteTag.tag_id == Tag.id)
        .filter(NoteTag.note_id == note.id)
        .order_by(Tag.name.asc())
        .all()
    )
    return NotePublic(
        id=note.id,
        title=note.title,
        content=note.content,
        is_pinned=note.is_pinned,
        is_favorited=note.is_favorited,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=[TagPublic.model_validate(t) for t in tag_rows],
    )


@router.get(
    "",
    response_model=NotesListResponse,
    summary="List notes",
    description="List notes for the current user, optionally filtered by pinned/favorited/tag and searched by query.",
)
def list_notes(
    q: Optional[str] = Query(default=None, description="Search query applied to title/content."),
    tag_id: Optional[UUID] = Query(default=None, description="Filter notes that have this tag attached."),
    pinned: Optional[bool] = Query(default=None, description="Filter by pinned flag."),
    favorited: Optional[bool] = Query(default=None, description="Filter by favorited flag."),
    limit: int = Query(default=50, ge=1, le=200, description="Max number of notes returned."),
    offset: int = Query(default=0, ge=0, description="Offset for pagination."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotesListResponse:
    """List/search notes."""
    query = db.query(Note).filter(Note.user_id == user.id)

    if pinned is not None:
        query = query.filter(Note.is_pinned == pinned)
    if favorited is not None:
        query = query.filter(Note.is_favorited == favorited)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Note.title.ilike(like), Note.content.ilike(like)))
    if tag_id:
        query = query.join(NoteTag, NoteTag.note_id == Note.id).filter(NoteTag.tag_id == tag_id)

    total = query.count()
    notes = query.order_by(desc(Note.is_pinned), desc(Note.updated_at)).offset(offset).limit(limit).all()
    return NotesListResponse(items=[_note_to_public(db, n) for n in notes], total=total)


@router.post(
    "",
    response_model=NotePublic,
    status_code=201,
    summary="Create note",
    description="Create a new note for the current user.",
)
def create_note(
    req: NoteCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotePublic:
    """Create a new note."""
    now = datetime.now(timezone.utc)
    note = Note(
        id=__import__("uuid").uuid4(),
        user_id=user.id,
        title=req.title or "",
        content=req.content or "",
        is_pinned=bool(req.is_pinned),
        is_favorited=bool(req.is_favorited),
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_to_public(db, note)


@router.get(
    "/{note_id}",
    response_model=NotePublic,
    summary="Get note",
    description="Fetch a single note by ID (must belong to current user).",
)
def get_note(
    note_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotePublic:
    """Get note by ID."""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    return _note_to_public(db, note)


@router.patch(
    "/{note_id}",
    response_model=NotePublic,
    summary="Update note",
    description="Update note fields (title/content/pinned/favorited).",
)
def update_note(
    note_id: UUID,
    req: NoteUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotePublic:
    """Update note."""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    if req.title is not None:
        note.title = req.title
    if req.content is not None:
        note.content = req.content
    if req.is_pinned is not None:
        note.is_pinned = req.is_pinned
    if req.is_favorited is not None:
        note.is_favorited = req.is_favorited

    # updated_at is maintained by DB trigger in schema, but we also set it to keep API consistent.
    note.updated_at = datetime.now(timezone.utc)

    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_to_public(db, note)


@router.delete(
    "/{note_id}",
    status_code=204,
    summary="Delete note",
    description="Delete a note (must belong to current user).",
)
def delete_note(
    note_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete note."""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    db.delete(note)
    db.commit()
    return None


@router.post(
    "/{note_id}/tags/{tag_id}",
    response_model=NotePublic,
    summary="Attach tag to note",
    description="Attach a tag to a note (both must belong to current user).",
)
def attach_tag(
    note_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotePublic:
    """Attach a tag to a note."""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found.")

    existing = db.query(NoteTag).filter(NoteTag.note_id == note_id, NoteTag.tag_id == tag_id).first()
    if existing:
        return _note_to_public(db, note)

    rel = NoteTag(
        note_id=note_id,
        tag_id=tag_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rel)
    db.commit()
    db.refresh(note)
    return _note_to_public(db, note)


@router.delete(
    "/{note_id}/tags/{tag_id}",
    response_model=NotePublic,
    summary="Detach tag from note",
    description="Detach a tag from a note (both must belong to current user).",
)
def detach_tag(
    note_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotePublic:
    """Detach a tag from a note."""
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    rel = db.query(NoteTag).filter(NoteTag.note_id == note_id, NoteTag.tag_id == tag_id).first()
    if not rel:
        # idempotent
        return _note_to_public(db, note)

    db.delete(rel)
    db.commit()
    db.refresh(note)
    return _note_to_public(db, note)
