from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .provenance import append_extraction_log, sha256_file, utc_now, write_sha256_sidecar


USER_AGENT = "vr-saude-ambiental/0.1 (+reproducible epidemiology project)"


SAMPLE_SOURCES: dict[str, dict[str, str]] = {
    "ibge_9514_vr_2022": {
        "url": "https://apisidra.ibge.gov.br/values/t/9514/n6/3306305/p/2022",
        "filename": "ibge_sidra_9514_vr_2022.json",
        "period": "2022",
        "territory": "3306305",
    },
    "sim_2024_csv": {
        "url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SIM/csv/DO24OPEN_csv.zip",
        "filename": "sim_mortalidade_geral_2024_csv.zip",
        "period": "2024",
        "territory": "RJ",
    },
    "sivep_dictionary": {
        "url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/dicionario-de-dados-2019-a-2025.pdf",
        "filename": "sivep_srag_dicionario_2019_2025.pdf",
        "period": "2019-2025",
        "territory": "Brasil",
    },
    "sivep_2019_parquet": {
        "url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2019/INFLUD19-23-03-2026.parquet",
        "filename": "sivep_srag_2019_2026-03-23.parquet",
        "period": "2019",
        "territory": "RJ",
    },
}


def _download_once(url: str, destination: Path, timeout: int) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def download_public_file(
    root: Path,
    source_id: str,
    url: str,
    filename: str,
    period: str,
    territory: str,
    logger: logging.Logger | None = None,
    retries: int = 3,
    timeout: int = 120,
) -> Path:
    """Download one public resource idempotently and register its hash."""
    logger = logger or logging.getLogger("vr_saude")
    destination = root / "data" / "raw" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    extraction_id = f"{source_id}_{uuid.uuid4().hex[:8]}"
    started = utc_now()
    sidecar = Path(f"{destination}.sha256")

    if destination.exists() and sidecar.exists():
        current_digest = sha256_file(destination)
        declared = sidecar.read_text(encoding="utf-8").split()[0]
        if current_digest == declared:
            append_extraction_log(
                root,
                {
                    "extraction_id": extraction_id,
                    "source_id": source_id,
                    "operation": "download",
                    "requested_period": period,
                    "territory": territory,
                    "started_at": started,
                    "finished_at": utc_now(),
                    "status": "skipped_existing_verified",
                    "sha256": current_digest,
                    "raw_path": str(destination.relative_to(root)),
                    "validation_summary": "existing file and sidecar hash match",
                },
            )
            logger.info("Skipping verified raw file: %s", destination)
            return destination

    temporary = destination.with_name(f".{destination.name}.part")
    error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            if temporary.exists():
                temporary.unlink()
            logger.info("Downloading %s (attempt %s/%s)", url, attempt, retries)
            _download_once(url, temporary, timeout)
            temporary.replace(destination)
            digest = sha256_file(destination)
            write_sha256_sidecar(destination, digest)
            append_extraction_log(
                root,
                {
                    "extraction_id": extraction_id,
                    "source_id": source_id,
                    "operation": "download",
                    "requested_period": period,
                    "territory": territory,
                    "started_at": started,
                    "finished_at": utc_now(),
                    "status": "downloaded",
                    "sha256": digest,
                    "raw_path": str(destination.relative_to(root)),
                    "validation_summary": "HTTP response written and SHA-256 generated",
                },
            )
            logger.info("Downloaded %s (%s)", destination, digest)
            return destination
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            error = exc
            logger.warning("Download failed: %s", exc)
            if attempt < retries:
                time.sleep(min(2 * attempt, 5))

    append_extraction_log(
        root,
        {
            "extraction_id": extraction_id,
            "source_id": source_id,
            "operation": "download",
            "requested_period": period,
            "territory": territory,
            "started_at": started,
            "finished_at": utc_now(),
            "status": "failed",
            "raw_path": str(destination.relative_to(root)),
            "error_or_note": f"{type(error).__name__}: {error}",
        },
    )
    raise RuntimeError(f"Could not download {url}") from error


def save_json_probe(root: Path, source_id: str, payload: object, filename: str) -> Path:
    """Save a small already-fetched JSON payload while preserving provenance."""
    destination = root / "data" / "raw" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = sha256_file(destination)
    write_sha256_sidecar(destination, digest)
    append_extraction_log(
        root,
        {
            "extraction_id": f"{source_id}_probe",
            "source_id": source_id,
            "operation": "save_json_probe",
            "requested_period": "2022",
            "territory": "3306305",
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "status": "downloaded",
            "sha256": digest,
            "raw_path": str(destination.relative_to(root)),
            "validation_summary": "JSON payload saved with SHA-256",
        },
    )
    return destination
