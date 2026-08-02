from __future__ import annotations

import csv
import html
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .provenance import append_extraction_log, sha256_file, utc_now, write_sha256_sidecar
from .sih_tabnet import (
    SIH_RESIDENCE_DEF_URL,
    SIH_RESIDENCE_QUERY_URL,
    USER_AGENT,
    _archive_value,
    _definition_municipality_value,
    _get,
)


ALL_MUNICIPALITIES_VALUE = "TODAS_AS_CATEGORIAS__"
MORBIDITY_LINE = "Lista_Morb__CID-10"
TARGET_LABELS = {
    "resp_all": "10 Doenças do aparelho respiratório",
    "pneumonia": "Pneumonia",
    "acute_bronchitis_bronchiolitis": "Bronquite aguda e bronquiolite aguda",
    "copd": "Bronquite enfisema e outr doenç pulm obstr crôn",
    "asthma": "Asma",
    "pneumoconiosis": "Pneumoconiose",
}


@dataclass(frozen=True)
class SihMorbidityResult:
    year: int
    month: int
    geography: str
    municipality_selector: str
    municipality_code: str
    rows: dict[str, int]
    labels: dict[str, str]
    response: bytes


def _canonical(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower().replace("..", "")
    return re.sub(r"\s+", " ", value).strip()


def _target_id(label: str) -> str | None:
    canonical = _canonical(label)
    if canonical.startswith("10 doencas do aparelho respiratorio"):
        return "resp_all"
    if canonical == "pneumonia":
        return "pneumonia"
    if canonical.startswith("bronquite aguda e bronquiolite aguda"):
        return "acute_bronchitis_bronchiolitis"
    if canonical.startswith("bronquite enfisema e outr doen"):
        return "copd"
    if canonical == "asma":
        return "asthma"
    if canonical.startswith("pneumoconiose"):
        return "pneumoconiosis"
    return None


def _parse_rows(response: str) -> tuple[dict[str, int], dict[str, str]]:
    match = re.search(r"<PRE>(.*?)</PRE>", response, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("SIH TabNet morbidity response did not contain a PRE table")
    rows: dict[str, int] = {}
    labels: dict[str, str] = {}
    for raw_line in html.unescape(match.group(1)).splitlines():
        line = raw_line.strip()
        if not line.startswith('"') or ";" not in line:
            continue
        label_match = re.match(r'^"([^"]+)";\s*([0-9.,-]+)', line)
        if not label_match:
            continue
        label = label_match.group(1).strip()
        if _canonical(label) in {"total", "total geral"}:
            continue
        target_id = _target_id(label)
        if target_id is None:
            continue
        raw_value = label_match.group(2)
        value = 0 if raw_value == "-" else int(raw_value.replace(".", "").replace(",", ""))
        rows[target_id] = value
        labels[target_id] = label
    return rows, labels


def _query_from_definition(
    root: Path,
    definition: str,
    year: int,
    month: int,
    geography: str,
    municipality_selector: str,
    timeout: int,
) -> SihMorbidityResult:
    archive = _archive_value(definition, year, month)
    fields = [
        ("Linha", MORBIDITY_LINE),
        ("Coluna", "--Não-Ativa--"),
        ("Incremento", "Internações"),
        ("Arquivos", archive),
        ("SMunicípio", municipality_selector),
        (f"S{MORBIDITY_LINE}", ALL_MUNICIPALITIES_VALUE),
        ("zeradas", "exibirlz"),
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
    if "Tabela de conversao nao encontrada" in decoded or "Exception" in decoded:
        raise ValueError(f"SIH TabNet rejected morbidity query for {year}-{month:02d}")
    rows, labels = _parse_rows(decoded)
    municipality_code = _municipality_code(root)
    return SihMorbidityResult(
        year=year,
        month=month,
        geography=geography,
        municipality_selector=municipality_selector,
        municipality_code=municipality_code,
        rows=rows,
        labels=labels,
        response=payload,
    )


def _municipality_code(root: Path) -> str:
    territories = load_config("territories.yml", root)
    return str(territories["volta_redonda"]["datasus_code_6_expected"])


def query_morbidity_month(
    root: Path,
    definition: str,
    year: int,
    month: int,
    geography: str,
    municipality_selector: str,
    timeout: int = 60,
) -> SihMorbidityResult:
    return _query_from_definition(
        root,
        definition,
        year,
        month,
        geography,
        municipality_selector,
        timeout,
    )


def _periods(start_year: int, start_month: int, end_year: int, end_month: int) -> list[tuple[int, int]]:
    if not 1 <= start_month <= 12 or not 1 <= end_month <= 12:
        raise ValueError("months must be between 1 and 12")
    if (start_year, start_month) > (end_year, end_month):
        raise ValueError("start period must not be after end period")
    return [
        (year, month)
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
        if (start_year, start_month) <= (year, month) <= (end_year, end_month)
    ]


def _selectors(root: Path, definition: str) -> dict[str, str]:
    return {
        "rj_total": ALL_MUNICIPALITIES_VALUE,
        "volta_redonda": _definition_municipality_value(
            definition,
            _municipality_code(root),
        ),
    }


def _raw_path(root: Path, geography: str, year: int, month: int) -> Path:
    return root / "data" / "raw" / f"sih_tabnet_nrrj_morbidity_{geography}_{year}_{month:02d}.html"


def _save_raw(root: Path, result: SihMorbidityResult) -> Path:
    destination = _raw_path(root, result.geography, result.year, result.month)
    sidecar = Path(f"{destination}.sha256")
    if destination.exists():
        if not sidecar.exists():
            raise FileExistsError(f"raw response exists without hash sidecar: {destination}")
        declared = sidecar.read_text(encoding="utf-8").split()[0]
        actual = sha256_file(destination)
        if actual != declared:
            raise FileExistsError(f"raw response exists with hash mismatch: {destination}")
        status = "skipped_existing_verified"
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(result.response)
        actual = sha256_file(destination)
        write_sha256_sidecar(destination, actual)
        status = "downloaded"
    append_extraction_log(
        root,
        {
            "extraction_id": f"sih_tabnet_nrrj_morbidity_{result.geography}_{result.year}_{result.month:02d}",
            "source_id": "sih_tabnet_nrrj_morbidity",
            "operation": "tabnet_post_morbidity_list",
            "requested_period": f"{result.year}-{result.month:02d}",
            "territory": result.geography,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "status": status,
            "records": sum(result.rows.values()),
            "sha256": sha256_file(destination),
            "raw_path": str(destination.relative_to(root)),
            "validation_summary": "TabNet Lista Morb CID-10 por município de residência; HTML preservado",
        },
    )
    return destination


def _query_and_save(
    root: Path,
    definition: str,
    period: tuple[int, int],
    geography: str,
    selector: str,
    timeout: int,
) -> tuple[SihMorbidityResult, Path]:
    destination = _raw_path(root, geography, period[0], period[1])
    sidecar = Path(f"{destination}.sha256")
    if destination.exists():
        if not sidecar.exists():
            raise FileExistsError(f"raw response exists without hash sidecar: {destination}")
        declared = sidecar.read_text(encoding="utf-8").split()[0]
        actual = sha256_file(destination)
        if actual != declared:
            raise FileExistsError(f"raw response exists with hash mismatch: {destination}")
        payload = destination.read_bytes()
        rows, labels = _parse_rows(payload.decode("latin1"))
        return (
            SihMorbidityResult(
                year=period[0],
                month=period[1],
                geography=geography,
                municipality_selector=selector,
                municipality_code=_municipality_code(root),
                rows=rows,
                labels=labels,
                response=payload,
            ),
            destination,
        )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            result = query_morbidity_month(root, definition, *period, geography, selector, timeout)
            return result, _save_raw(root, result)
        except (OSError, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1 + attempt)
    assert last_error is not None
    raise last_error


def _derived_rows(
    root: Path,
    results: dict[tuple[int, int, str], SihMorbidityResult],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for (year, month, geography), rj_result in sorted(results.items()):
        if geography != "rj_total":
            continue
        vr_result = results[(year, month, "volta_redonda")]
        for outcome_id, outcome_label in TARGET_LABELS.items():
            rj_value = rj_result.rows.get(outcome_id)
            vr_value = vr_result.rows.get(outcome_id)
            if rj_value is None or vr_value is None:
                continue
            rj_path = _raw_path(root, "rj_total", year, month)
            vr_path = _raw_path(root, "volta_redonda", year, month)
            rj_hash = sha256_file(rj_path)
            vr_hash = sha256_file(vr_path)
            for geography, value, source_paths, source_hashes in [
                ("rj_total", rj_value, str(rj_path.relative_to(root)), rj_hash),
                ("volta_redonda", vr_value, str(vr_path.relative_to(root)), vr_hash),
                (
                    "rest_of_rj_excluding_vr",
                    rj_value - vr_value,
                    f"{rj_path.relative_to(root)};{vr_path.relative_to(root)}",
                    f"{rj_hash};{vr_hash}",
                ),
            ]:
                output.append(
                    {
                        "year": year,
                        "month": month,
                        "period": f"{year:04d}-{month:02d}",
                        "geography": geography,
                        "municipality_code_datasus": rj_result.municipality_code,
                        "outcome_id": outcome_id,
                        "outcome_label": outcome_label,
                        "value": value,
                        "unit": "internações agregadas pelo SIH",
                        "source_paths": source_paths,
                        "source_sha256s": source_hashes,
                    }
                )
    return output


def query_morbidity_series(
    root: Path,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    workers: int = 2,
    timeout: int = 60,
) -> tuple[Path, Path]:
    if workers < 1 or workers > 8:
        raise ValueError("workers must be between 1 and 8")
    periods = _periods(start_year, start_month, end_year, end_month)
    if len(periods) > 120:
        raise ValueError("a single morbidity series query is limited to 120 months")
    definition = _get(SIH_RESIDENCE_DEF_URL, timeout).decode("latin1")
    selectors = _selectors(root, definition)
    jobs = [
        (period, geography, selector)
        for period in periods
        for geography, selector in selectors.items()
    ]
    results: dict[tuple[int, int, str], SihMorbidityResult] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_query_and_save, root, definition, period, geography, selector, timeout): (
                period,
                geography,
            )
            for period, geography, selector in jobs
        }
        for future in as_completed(futures):
            result, _ = future.result()
            results[(result.year, result.month, result.geography)] = result
    rows = _derived_rows(root, results)
    destination = root / "data" / "interim" / f"sih_morbidity_{start_year}_{end_year}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "year",
        "month",
        "period",
        "geography",
        "municipality_code_datasus",
        "outcome_id",
        "outcome_label",
        "value",
        "unit",
        "source_paths",
        "source_sha256s",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    expected = len(periods) * len(TARGET_LABELS) * 3
    report = {
        "source_id": "sih_tabnet_nrrj_morbidity",
        "geography": "residência; RJ total, Volta Redonda e restante do RJ excluindo VR",
        "municipality_code_datasus": _municipality_code(root),
        "period_start": f"{start_year:04d}-{start_month:02d}",
        "period_end": f"{end_year:04d}-{end_month:02d}",
        "rows": len(rows),
        "expected_rows": expected,
        "raw_response_count": len(results),
        "target_labels": TARGET_LABELS,
        "derived_comparator": "rj_total - volta_redonda",
        "negative_values": [row for row in rows if int(row["value"]) < 0],
        "status": (
            "validated_structure_only_no_epidemiological_estimate"
            if len(rows) == expected and not any(int(row["value"]) < 0 for row in rows)
            else "incomplete_or_inconsistent_series"
        ),
        "notes": [
            "SIH counts are aggregated hospitalizations/AIH, not unique persons or incident cases.",
            "Rest of RJ is algebraically derived after querying the RJ total and Volta Redonda by residence.",
            "TabNet's Lista Morb CID-10 is used for the named respiratory groups; exact CID audit remains required.",
            "In the official TabNet legend, '-' is a numeric zero not resulting from rounding and is retained as 0.",
            "No denominator, rate, confidence interval, or causal estimate is produced here.",
        ],
    }
    report_path = root / "reports" / "quality" / f"sih_morbidity_{start_year}_{end_year}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination, report_path
