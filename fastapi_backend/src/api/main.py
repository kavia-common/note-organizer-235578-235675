from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_settings
from src.api.routes_auth import router as auth_router
from src.api.routes_notes import router as notes_router
from src.api.routes_tags import router as tags_router

settings = get_settings()

openapi_tags = [
    {"name": "meta", "description": "Health and documentation helpers."},
    {"name": "auth", "description": "User registration and login (JWT)."},
    {"name": "notes", "description": "Notes CRUD, pin/favorite, list/search, and note-tag relations."},
    {"name": "tags", "description": "Tags CRUD."},
]

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
    openapi_tags=openapi_tags,
)

def _parse_cors_origins(raw: str | None) -> list[str]:
    """Parse comma-separated CORS origins.

    Supports '*', empty, and standard comma-separated URL origins.
    """
    if not raw:
        return ["*"]
    cleaned = [o.strip() for o in raw.split(",") if o.strip()]
    return cleaned or ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    tags=["meta"],
    summary="Health check",
    description="Simple health check endpoint.",
)
def health_check():
    """Health check."""
    return {"message": "Healthy"}


@app.get(
    "/docs/auth",
    tags=["meta"],
    summary="Auth usage",
    description="Explains how to authenticate with the API using JWT Bearer tokens.",
)
def auth_usage():
    """Auth usage docs helper."""
    return {
        "how_to": [
            "1) POST /auth/register with {email,password,display_name?} to create an account.",
            "2) POST /auth/login with {email,password} to get access_token.",
            "3) Call protected endpoints with header: Authorization: Bearer <access_token>",
        ]
    }


app.include_router(auth_router)
app.include_router(notes_router)
app.include_router(tags_router)
