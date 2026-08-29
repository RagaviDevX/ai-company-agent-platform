import json
from datetime import datetime, timezone
from pathlib import Path

from backend.config.settings import settings


def write_log(event: dict) -> None:
    Path(settings.logs_dir).mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False)
    with open(Path(settings.logs_dir) / f"{day}.jsonl", "a", encoding="utf-8") as f:
        f.write(line + "\n")


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
