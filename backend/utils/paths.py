import re
import uuid
from pathlib import Path

from backend.config.settings import settings

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9_.\-]")


def ensure_dirs() -> None:
    for p in (
        Path(settings.uploads_dir),
        Path(settings.logs_dir),
        Path(settings.qdrant_path),
        Path(settings.sqlite_db).parent,
    ):
        p.mkdir(parents=True, exist_ok=True)


def load_prompt(name: str) -> str:
    path = Path(settings.prompts_dir) / name
    return path.read_text(encoding="utf-8").strip()


def safe_upload_name(filename: str) -> str:
    """Reduce a client-supplied filename to a single safe path segment.

    ``Path(filename).name`` strips any directory components, which defeats
    ``../`` traversal and absolute paths (``/etc/passwd``, ``C:\\...``).
    Remaining characters are restricted to a conservative allow-list so the
    name is safe across every filesystem we deploy to.
    """
    name = Path(filename or "").name.strip()
    if not name or name in {".", ".."}:
        raise ValueError("Invalid or missing filename.")
    name = _SAFE_CHARS.sub("_", name)
    return name[:200]


def resolve_upload_path(filename: str) -> Path:
    """Return a safe, collision-free destination path inside ``uploads_dir``.

    Raises ``ValueError`` for unsafe filenames instead of silently writing
    outside the uploads directory.
    """
    ensure_dirs()
    safe_name = safe_upload_name(filename)
    uploads_root = Path(settings.uploads_dir).resolve()
    dest = (uploads_root / safe_name).resolve()
    if dest.parent != uploads_root:
        # Defense in depth: should be unreachable given safe_upload_name(),
        # but never write outside the uploads directory.
        raise ValueError("Invalid upload path.")
    if dest.exists():
        dest = dest.with_name(f"{dest.stem}_{uuid.uuid4().hex[:8]}{dest.suffix}")
    return dest
