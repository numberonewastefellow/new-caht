"""Logo / logotype asset storage for application settings (file-store backed).

Kept separate from the settings blob because logos are binary assets stored under
fixed file-store ids (per tenant) rather than columns on the settings row.
"""

import os
from io import BytesIO

from fastapi import HTTPException
from fastapi import Response
from fastapi import UploadFile

from om.configs.constants import FileOrigin
from om.file_store.file_store import get_default_file_store
from om.utils.logger import setup_logger

logger = setup_logger()

_LOGO_FILE_ID = "__app_logo__"
_LOGOTYPE_FILE_ID = "__app_logotype__"
_VALID_EXTENSIONS = (".png", ".jpg", ".jpeg")


def _file_id(is_logotype: bool) -> str:
    return _LOGOTYPE_FILE_ID if is_logotype else _LOGO_FILE_ID


def get_logo_file_id() -> str:
    """File-store id of the uploaded logo (used by the runtime override lookup)."""
    return _LOGO_FILE_ID


def get_logotype_file_id() -> str:
    """File-store id of the uploaded logotype (used by the runtime override lookup)."""
    return _LOGOTYPE_FILE_ID


def _guess_file_type(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


def save_logo_from_path(path: str, is_logotype: bool = False) -> bool:
    """Persist a logo asset from a local file path (used by DB seeding)."""
    if not os.path.isfile(path) or not path.lower().endswith(_VALID_EXTENSIONS):
        logger.error("Invalid logo file — only .png, .jpg, and .jpeg files are allowed")
        return False

    with open(path, "rb") as handle:
        content = BytesIO(handle.read())

    get_default_file_store().save_file(
        content=content,
        display_name=path,
        file_origin=FileOrigin.OTHER,
        file_type=_guess_file_type(path),
        file_id=_file_id(is_logotype),
    )
    return True


def save_logo(file: UploadFile, is_logotype: bool) -> None:
    if not file.filename or not file.filename.lower().endswith(_VALID_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type — only .png, .jpg, and .jpeg are allowed.",
        )
    get_default_file_store().save_file(
        content=file.file,
        display_name=file.filename,
        file_origin=FileOrigin.OTHER,
        file_type=file.content_type or "image/png",
        file_id=_file_id(is_logotype),
    )


def fetch_logo_response(is_logotype: bool) -> Response:
    try:
        stored = get_default_file_store().get_file_with_mime_type(
            _file_id(is_logotype)
        )
        if stored is None:
            raise ValueError("logo asset not found")
    except Exception:
        raise HTTPException(status_code=404, detail="No logo file found")
    return Response(content=stored.data, media_type=stored.mime_type)
