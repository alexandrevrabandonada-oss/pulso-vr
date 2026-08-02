from __future__ import annotations

import html
import csv
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .provenance import append_extraction_log, sha256_file, utc_now, write_sha256_sidecar


SIH_RESIDENCE_DEF_URL = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrrj"
SIH_RESIDENCE_QUERY_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/nrrj"
USER_AGENT = "vr-saude-ambiental/0.1 (+reproducible epidemiology project)"


@dataclass(frozen=True)
class SihQueryResult:
    year: int
    month: int
    archive: str
    municipality_value: str
    municipality_code: str
    municipality_name: str
    hospitalizations: int
    response: bytes


def _get(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _municipality_code(root: Path) -> str:
    territories = load_config("territories.yml", root)
    return str(territories["volta_redonda"]["datasus_code_6_expected"])


def _definition_municipality_value(definition: str, code: str) -> str:
    pattern = (
        r'<OPTION\s+VALUE="([^"]+)"[^>]*>\s*'
        + re.escape(code)
        + r'\s+VOLTA\s+REDONDA'
    )
    match = re.search(pattern, html.unescape(definition), re.IGNORECASE)
    if not match:
        raise LookupError(f"SIH TabNet definition did not expose municipality {code} Volta Redonda")
    return match.group(1)


def _archive_value(definition: str, year: int, month: int) -> str:
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    archive = f"nrrj{year % 100:02d}{month:02d}.dbf"
    if not re.search(rf'<OPTION\s+VALUE="{re.escape(archive)}"', definition, re.IGNORECASE):
        raise LookupError(f"SIH TabNet definition does not list archive {archive}")
    return archive


def _parse_hospitalizations(response: str, municipality_code: str) -> int:
    match = re.search(rf'"{re.escape(municipality_code)}\s+VOLTA REDONDA";([0-9.,-]+)', response)
    if not match:
        raise ValueError("SIH TabNet response did not contain the Volta Redonda row")
    value = match.group(1).replace(".", "").replace(",", "")
    return int(value)


def _query_from_definition(root: Path, definition: str, year: int, month: int, timeout: int) -> SihQueryResult:
    municipality_code = _municipality_code(root)
    municipality_value = _definition_municipality_value(definition, municipality_code)
    archive = _archive_value(definition, year, month)
    fields = [
        ("Linha", "Município"),
        ("Coluna", "--Não-Ativa--"),
        ("Incremento", "Internações"),
        ("Arquivos", archive),
        ("SMunicípio", municipality_value),
        ("formato", "prn"),
        ("mostre", "Mostra"),
    ]
    body = urllib.parse.urlencode(fields, encoding="latin1").encode("ascii")
    request = urllib.request.Request(
        SIH_RESIDENCE_QUERY_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    decoded = payload.decode("latin1")
    return SihQueryResult(
        year=year,
        month=month,
        archive=archive,
        municipality_value=municipality_value,
        municipality_code=municipality_code,
        municipality_name="Volta Redonda",
        hospitalizations=_parse_hospitalizations(decoded, municipality_code),
        response=payload,
    )


def query_residence(root: Path, year: int, month: int, timeout: int = 60) -> SihQueryResult:
    definition = _get(SIH_RESIDENCE_DEF_URL, timeout).decode("latin1")
    return _query_from_definition(root, definition, year, month, timeout)


def query_residence_series(
    root: Path,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    timeout: int = 60,
) -> list[SihQueryResult]:
    start = (start_year, start_month)
    end = (end_year, end_month)
    if not 1 <= start_month <= 12 or not 1 <= end_month <= 12:
        raise ValueError("months must be between 1 and 12")
    if start > end:
        raise ValueError("start period must not be after end period")
    periods = [
        (year, month)
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
        if start <= (year, month) <= end
    ]
    if len(periods) > 120:
        raise ValueError("a single series query is limited to 120 months")
    definition = _get(SIH_RESIDENCE_DEF_URL, timeout).decode("latin1")
    return [_query_from_definition(root, definition, year, month, timeout) for year, month in periods]


def _log_saved_response(root: Path, result: SihQueryResult, destination: Path, digest: str, status: str) -> None:
    append_extraction_log(
        root,
        {
            "extraction_id": f"sih_tabnet_nrrj_{result.year}_{result.month:02d}",
            "source_id": "sih_tabnet_nrrj",
            "operation": "tabnet_post",
            "requested_period": f"{result.year}-{result.month:02d}",
            "territory": result.municipality_code,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "status": status,
            "records": result.hospitalizations,
            "sha256": digest,
            "raw_path": str(destination.relative_to(root)),
            "validation_summary": "TabNet POST por residência; resposta HTML preservada",
        },
    )


def save_query_response(root: Path, result: SihQueryResult) -> Path:
    destination = root / "data" / "raw" / f"sih_tabnet_nrrj_{result.year}_{result.month:02d}.html"
    sidecar = Path(f"{destination}.sha256")
    if destination.exists():
        if not sidecar.exists():
            raise FileExistsError(f"raw response exists without hash sidecar: {destination}")
        declared = sidecar.read_text(encoding="utf-8").split()[0]
        actual = sha256_file(destination)
        if actual != declared:
            raise FileExistsError(f"raw response exists with hash mismatch: {destination}")
        _log_saved_response(root, result, destination, actual, "skipped_existing_verified")
        return destination
    destination.write_bytes(result.response)
    digest = sha256_file(destination)
    write_sha256_sidecar(destination, digest)
    _log_saved_response(root, result, destination, digest, "downloaded")
    return destination


def write_harmonized_series(root: Path, results: list[SihQueryResult]) -> tuple[Path, Path]:
    if not results:
        raise ValueError("series cannot be empty")
    periods = [(item.year, item.month) for item in results]
    if len(periods) != len(set(periods)):
        raise ValueError("series contains duplicate year-month keys")
    if any(item.hospitalizations < 0 for item in results):
        raise ValueError("series contains negative hospitalization counts")
    ordered = sorted(results, key=lambda item: (item.year, item.month))
    destination = root / "data" / "interim" / (
        f"sih_nrrj_monthly_{ordered[0].year}_{ordered[-1].year}.csv"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "year",
        "month",
        "period",
        "source_file",
        "source_sha256",
        "municipality_code_datasus",
        "municipality_name",
        "measure",
        "value",
        "unit",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in ordered:
            raw_path = root / "data" / "raw" / f"sih_tabnet_nrrj_{item.year}_{item.month:02d}.html"
            writer.writerow(
                {
                    "year": item.year,
                    "month": item.month,
                    "period": f"{item.year:04d}-{item.month:02d}",
                    "source_file": str(raw_path.relative_to(root)),
                    "source_sha256": sha256_file(raw_path),
                    "municipality_code_datasus": item.municipality_code,
                    "municipality_name": item.municipality_name,
                    "measure": "Internações",
                    "value": item.hospitalizations,
                    "unit": "internação agregada pelo SIH",
                }
            )
    counts = Counter(periods)
    duplicate_periods = [
        f"{year:04d}-{month:02d}"
        for year, month in sorted(period for period, count in counts.items() if count > 1)
    ]
    expected_periods = [
        (year, month)
        for year in range(ordered[0].year, ordered[-1].year + 1)
        for month in range(1, 13)
        if (ordered[0].year, ordered[0].month) <= (year, month) <= (ordered[-1].year, ordered[-1].month)
    ]
    missing_periods = [
        f"{year:04d}-{month:02d}"
        for year, month in expected_periods
        if (year, month) not in counts
    ]
    annual_totals: dict[str, int] = {}
    for item in ordered:
        annual_totals[str(item.year)] = annual_totals.get(str(item.year), 0) + item.hospitalizations
    report = {
        "source_id": "sih_tabnet_nrrj",
        "geography": "residência em Volta Redonda",
        "municipality_code_datasus": ordered[0].municipality_code,
        "period_start": f"{ordered[0].year:04d}-{ordered[0].month:02d}",
        "period_end": f"{ordered[-1].year:04d}-{ordered[-1].month:02d}",
        "rows": len(ordered),
        "total_aggregated_events": sum(item.hospitalizations for item in ordered),
        "annual_aggregated_events": annual_totals,
        "duplicate_periods": duplicate_periods,
        "missing_periods": missing_periods,
        "negative_values": [],
        "raw_files": [
            {
                "path": str((root / "data" / "raw" / f"sih_tabnet_nrrj_{item.year}_{item.month:02d}.html").relative_to(root)),
                "sha256": sha256_file(root / "data" / "raw" / f"sih_tabnet_nrrj_{item.year}_{item.month:02d}.html"),
                "value": item.hospitalizations,
            }
            for item in ordered
        ],
        "status": (
            "validated_structure_only_no_epidemiological_estimate"
            if not duplicate_periods and not missing_periods
            else "incomplete_or_duplicate_series"
        ),
    }
    report_path = root / "reports" / "quality" / f"sih_series_{ordered[0].year}_{ordered[-1].year}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, report_path
