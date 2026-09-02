"""Evidence-photo upload hardening (S2-F05).

Three things a client-supplied ``UploadFile`` cannot be trusted for:

1. ``content_type`` — just an HTTP header the client sets; easy to spoof
   (e.g. rename a ``.html`` file to ``photo.png`` and send
   ``Content-Type: image/png``).
2. ``filename`` — used naively, it is a path-traversal vector
   (``../../app/main.py``) and a collision/overwrite risk.
3. Size — must be capped before the bytes are written to disk, not just
   checked after (``settings.upload_max_bytes`` already covers this at the
   route level; this module re-checks it defensively).

This module sniffs the real file type from its magic bytes, generates a
random, extension-safe filename, and writes it under ``settings.upload_dir``
via a resolved-path containment check so no input can ever escape that
directory.
"""

from __future__ import annotations

import uuid

from app.core.config import settings

__all__ = ["UploadRejectedError", "sniff_image_type", "save_upload"]


class UploadRejectedError(Exception):
    """Raised when an upload fails a hardening check."""

    def __init__(self, message: str, *, status_code: int = 415) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# Magic-byte signatures for the three formats the app claims to accept.
# Checked against the actual bytes, never the client-supplied header.
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    # WEBP is a RIFF container: bytes 0-3 "RIFF", bytes 8-11 "WEBP".
    "image/webp": (b"RIFF",),
}
_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def sniff_image_type(content: bytes) -> str | None:
    """Return the detected MIME type from magic bytes, or None if unrecognised."""
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    for mime_type, signatures in _SIGNATURES.items():
        if mime_type == "image/webp":
            continue  # handled above; RIFF alone is not sufficient evidence
        if any(content.startswith(sig) for sig in signatures):
            return mime_type
    return None


def save_upload(content: bytes, *, declared_content_type: str) -> str:
    """Validate and persist an uploaded image, returning its public URL path.

    Raises ``UploadRejectedError`` if the size, declared content-type, or
    sniffed magic bytes fail validation, or if the declared type disagrees
    with what the bytes actually are (the spoofing case).
    """
    if len(content) > settings.upload_max_bytes:
        raise UploadRejectedError("Image too large.", status_code=413)

    declared = (declared_content_type or "").lower()
    if declared not in settings.upload_allowed_mime_type_set:
        raise UploadRejectedError("Unsupported image type.", status_code=415)

    sniffed = sniff_image_type(content)
    if sniffed is None or sniffed not in settings.upload_allowed_mime_type_set:
        raise UploadRejectedError("File content does not match an allowed image type.")
    if sniffed != declared:
        raise UploadRejectedError("Declared content type does not match file contents.")

    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Filename is never derived from client input — sidesteps path traversal
    # (`../../x`), null-byte tricks, and overwrite collisions entirely.
    safe_name = f"{uuid.uuid4().hex}{_EXTENSIONS[sniffed]}"
    destination = (upload_dir / safe_name).resolve()

    # Defence in depth: confirm the resolved path is still inside upload_dir
    # before writing, in case upload_dir itself is ever misconfigured.
    if upload_dir.resolve() not in destination.parents:
        raise UploadRejectedError(
            "Resolved upload path escaped the upload directory.", status_code=500
        )

    destination.write_bytes(content)
    return f"/uploads/{safe_name}"
