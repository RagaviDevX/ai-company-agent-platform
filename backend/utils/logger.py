import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.config.settings import settings
from backend.utils.request_context import get_request_id

# Structured JSON-lines to stdout, in addition to the existing file log.
# Container platforms (Render, k8s, Docker Compose's `docker logs`, etc.)
# collect stdout directly -- writing structured JSON there means log
# aggregators can parse/filter/alert on it without tailing a file inside
# the container.
_stdout_logger = logging.getLogger("ai_company")
if not _stdout_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _stdout_logger.addHandler(_handler)
    _stdout_logger.setLevel(logging.INFO)
    _stdout_logger.propagate = False


def write_log(event: dict) -> None:
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    enriched = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": get_request_id(),
        **event,
    }
    line = json.dumps(enriched, ensure_ascii=False)
    with open(Path(settings.logs_dir) / f"{day}.jsonl", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    _stdout_logger.info(line)


def read_recent_logs(limit: int = 100) -> list[dict]:
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)
    files = sorted(Path(settings.logs_dir).glob("*.jsonl"), reverse=True)
    rows: list[dict] = []
    for file in files:
        for line in reversed(file.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(rows) >= limit:
                return rows
    return rows