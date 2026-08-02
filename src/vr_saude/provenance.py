from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_FIELDS = [
    "extraction_id",
    "source_id",
    "operation",
    "requested_period",
    "territory",
    "started_at",
    "finished_at",
    "status",
    "records",
    "sha256",
    "raw_path",
    "validation_summary",
    "error_or_note",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256_sidecar(path: Path, digest: str | None = None) -> Path:
    digest = digest or sha256_file(path)
    sidecar = Path(f"{path}.sha256")
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return sidecar


def append_extraction_log(root: Path, values: dict[str, Any]) -> None:
    path = root / "metadata" / "extraction_log.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    row = {field: "" for field in LOG_FIELDS}
    row.update({key: "" if value is None else str(value) for key, value in values.items()})
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
