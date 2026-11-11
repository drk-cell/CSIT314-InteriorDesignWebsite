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

import io
import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from PIL import Image

from app.api.deps import get_current_account
from app.domain.account import Account
from app.schemas.project import (
    PaletteEntryPublic,
    StoredImagePublic,
    TagSuggestionPublic,
)
from app.services.object_labels import engine_name
from app.services.tag_suggestion_service import suggest_tags

router = APIRouter(prefix="/images", tags=["images"])

MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
CONTENT_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

# Photos a designer keeps on a project live here and are served at /uploads/<name>.
# The default sits beside the backend so a clone behaves the same on any machine.
UPLOAD_ROOT = Path(
    os.environ.get(
        "APP_UPLOAD_DIR",
        str(Path(__file__).resolve().parents[2] / "uploads"),
    )
)
EXTENSIONS: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


async def _read_photo(file: UploadFile) -> bytes:
    """Return the bytes of an allowed photo, or raise the refusal."""
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
    return data


@router.post(
    "",
    response_model=StoredImagePublic,
    summary="Store an uploaded photo and return its address",
)
async def store_upload(
    actor: CurrentAccountDep,
    file: UploadFile = File(...),
) -> StoredImagePublic:
    """Keep a designer's photo so the project can show it later.

    The file is checked the same way as the tag reader: Pillow decodes it, so a
    renamed text file is refused. The name is random, so two designers can both
    upload ``kitchen.jpg`` without meeting.
    """
    data = await _read_photo(file)

    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as probe:
            width, height = probe.size
    except Exception as exc:  # Pillow raises several unrelated types
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That file is not an image",
        ) from exc

    declared = (file.content_type or "").lower()
    name = f"{uuid.uuid4().hex}{EXTENSIONS.get(declared, '.jpg')}"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    (UPLOAD_ROOT / name).write_bytes(data)

    return StoredImagePublic(url=f"/uploads/{name}", width=width, height=height)


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
        subject=suggestion.subject,
        objects=suggestion.objects,
    )
