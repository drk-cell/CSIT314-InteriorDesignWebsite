"""Turn an uploaded photo into catalogue tags.

One endpoint serves both roles. A customer uploads a room they want to copy and
searches with the tags that come back; a designer uploads their own work and
picks the tags that fit. The endpoint saves nothing: the file is read, described
and dropped.

The same analyser answers both roles on purpose. Tags only match if both sides
speak the same vocabulary, and the profile photo that produces a tag is the
photo that gives a project that same tag.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status

from app.api.deps import get_current_account
from app.domain.account import Account
from app.schemas.project import PaletteEntryPublic, TagSuggestionPublic
from app.services.object_labels import engine_name
from app.services.tag_suggestion_service import suggest_tags

router = APIRouter(prefix="/images", tags=["images"])

MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
CONTENT_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


@router.post(
    "/tags",
    response_model=TagSuggestionPublic,
    summary="Read an uploaded photo and return catalogue tags",
)
async def tags_for_upload(
    actor: CurrentAccountDep,
    file: UploadFile = File(...),
) -> TagSuggestionPublic:
    """Describe an uploaded photo. Any signed-in account may call this.

    The bytes are checked by Pillow, not by the declared type alone: a renamed
    text file is refused with 422.
    """
    declared = (file.content_type or "").lower()
    if declared and declared not in CONTENT_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG or WebP photo",
        )

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The photo is larger than 5 MB",
        )
    if not data:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The file is empty",
        )

    try:
        suggestion = suggest_tags(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return TagSuggestionPublic(
        palette=[
            PaletteEntryPublic(hex=entry.hex, percent=entry.percent)
            for entry in suggestion.palette
        ],
        tags=suggestion.tags,
        width=suggestion.width,
        height=suggestion.height,
        engine=engine_name(),
    )
