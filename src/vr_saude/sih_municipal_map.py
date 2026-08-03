from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .provenance import append_extraction_log, sha256_file, utc_now, write_sha256_sidecar
from .rates import RATE_MULTIPLIER, poisson_count_interval
from .sih_tabnet import SIH_RESIDENCE_DEF_URL, SIH_RESIDENCE_QUERY_URL, USER_AGENT, _archive_value


YEAR = 2022
QUERIES = {
    "resp_all": ("chapter", ["10"]),
    "pneumonia": ("lista", ["193"]),
    "acute_bronchitis_bronchiolitis": ("lista", ["194"]),
    "copd": ("lista", ["199"]),
    "asthma": ("lista", ["200"]),
    "pneumoconiosis": ("lista", ["202"]),
    "cardio_all": ("chapter", ["9"]),
    "hypertension": ("lista", ["169", "170"]),
    "ischemic_heart_disease": ("lista", ["171", "172"]),
    "acute_myocardial_infarction": ("lista", ["171"]),
    "pulmonary_embolism": ("lista", ["173"]),
    "cardiac_arrhythmia": ("lista", ["174"]),
    "heart_failure": ("lista", ["175"]),
    "cerebrovascular": ("lista", ["177", "178", "179", "180"]),
    "cardiorespiratory_all": ("chapter", ["9", "10"]),
}


def _population(root: Path, year: int) -> pd.DataFrame:
    path = root / "data" / "processed" / "population_rj_municipality.parquet"
    if not path.exists():
        raise FileNotFoundError(f"RJ municipality population is missing: {path}")
    population = pd.read_parquet(path).loc[lambda frame: frame["year"].eq(year)].copy()
    population["municipality_code_ibge"] = population["municipality_code_ibge"].astype(str)
    population["municipality_code_datasus"] = population["municipality_code_ibge"].str[:6]
    if len(population) != 92 or population["municipality_code_datasus"].nunique() != 92:
        raise ValueError(f"population denominator for {year} must contain 92 RJ municipalities")
    return population[["municipality_code_ibge", "municipality_code_datasus", "municipality_name", "population"]]


def _parse_municipal_rows(payload: bytes) -> dict[str, int]:
    text = html.unescape(payload.decode("latin1"))
    match = re.search(r"<PRE>(.*?)</PRE>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("SIH municipal map response did not contain a PRE table")
    rows: dict[str, int] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        row = re.match(r'^"\s*(\d{6})\s+[^";]+";\s*([0-9.,-]+)', line)
        if not row:
            continue
        raw_value = row.group(2)
        rows[row.group(1)] = 0 if raw_value == "-" else int(raw_value.replace(".", "").replace(",", ""))
    if len(rows) != 92:
        raise ValueError(f"SIH municipal map returned {len(rows)} municipalities, expected 92")
    return rows


def _raw_path(root: Path, year: int, outcome_id: str) -> Path:
    return root / "data" / "raw" / f"sih_tabnet_nrrj_municipal_map_v3_{year}_{outcome_id}.html"


def _query(root: Path, definition: str, year: int, outcome_id: str, timeout: int = 60) -> tuple[str, dict[str, int], Path]:
    kind, selectors = QUERIES[outcome_id]
    fields: list[tuple[str, str]] = [
        ("Linha", "Município"),
        ("Coluna", "--Não-Ativa--"),
        ("Incremento", "Internações"),
    ]
    fields.extend(("Arquivos", _archive_value(definition, year, month)) for month in range(1, 13))
    fields.append(("SMunicípio", "TODAS_AS_CATEGORIAS__"))
    selector_name = "SCapítulo_CID-10" if kind == "chapter" else "SLista_Morb__CID-10"
    fields.extend((selector_name, value) for value in selectors)
    fields.extend([("zeradas", "exibirlz"), ("formato", "prn"), ("mostre", "Mostra")])
    path = _raw_path(root, year, outcome_id)
    sidecar = Path(f"{path}.sha256")
    if path.exists() and sidecar.exists() and sha256_file(path) == sidecar.read_text(encoding="utf-8").split()[0]:
        payload = path.read_bytes()
    else:
        body = urllib.parse.urlencode(fields, encoding="latin1").encode("ascii")
        request = urllib.request.Request(
            SIH_RESIDENCE_QUERY_URL,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        write_sha256_sidecar(path, sha256_file(path))
    rows = _parse_municipal_rows(payload)
    append_extraction_log(root, {
        "extraction_id": f"sih_tabnet_nrrj_municipal_map_{year}_{outcome_id}",
        "source_id": "sih_tabnet_nrrj_municipal_map",
        "operation": "tabnet_post_municipality_residence_annual",
        "requested_period": str(year),
        "territory": "RJ municipalities",
        "started_at": utc_now(), "finished_at": utc_now(),
        "status": "skipped_existing_verified" if path.exists() else "downloaded",
        "records": sum(rows.values()), "sha256": sha256_file(path),
        "raw_path": str(path.relative_to(root)),
        "validation_summary": "92 municípios, residência, 12 arquivos mensais agregados; HTML preservado",
    })
    return outcome_id, rows, path


def build_sih_municipal_map(root: Path, year: int = YEAR, workers: int = 4) -> tuple[Path, Path, Path]:
    if year < 2008 or year > 2025:
        raise ValueError("SIH municipal map year must be between 2008 and 2025")
    if workers < 1 or workers > 8:
        raise ValueError("workers must be between 1 and 8")
    definition = urllib.request.urlopen(urllib.request.Request(SIH_RESIDENCE_DEF_URL, headers={"User-Agent": USER_AGENT}), timeout=60).read().decode("latin1")
    population = _population(root, year)
    futures = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for outcome_id in QUERIES:
            futures[executor.submit(_query, root, definition, year, outcome_id)] = outcome_id
        results = {}
        for future in as_completed(futures):
            outcome_id = futures[future]
            last_error = None
            for attempt in range(3):
                try:
                    results[outcome_id] = future.result()
                    break
                except (OSError, ValueError) as exc:
                    last_error = exc
                    if attempt < 2:
                        time.sleep(1 + attempt)
            if outcome_id not in results:
                raise last_error or RuntimeError(f"SIH map query failed: {outcome_id}")
    rows: list[dict[str, object]] = []
    for outcome_id in QUERIES:
        _, counts, path = results[outcome_id]
        for municipality in population.itertuples(index=False):
            count = int(counts[municipality.municipality_code_datasus])
            low, high = poisson_count_interval(count)
            rows.append({
                "year": year,
                "municipality_code_ibge": municipality.municipality_code_ibge,
                "municipality_code_datasus": municipality.municipality_code_datasus,
                "municipality_name": municipality.municipality_name,
                "outcome_id": outcome_id,
                "count": count,
                "population": int(municipality.population),
                "rate_per_100k": count / municipality.population * RATE_MULTIPLIER,
                "rate_ci_lower_per_100k": low / municipality.population * RATE_MULTIPLIER,
                "rate_ci_upper_per_100k": high / municipality.population * RATE_MULTIPLIER,
                "period_status": "provisional" if year >= 2025 else "source_year_observed",
                "source_path": str(path.relative_to(root)),
                "source_sha256": sha256_file(path),
            })
    frame = pd.DataFrame(rows)
    reconciliation: dict[str, dict[str, int]] = {}
    annual_path = root / "data" / "processed" / "respiratory_rates_annual.parquet"
    if annual_path.exists():
        annual = pd.read_parquet(annual_path)
        expected = (
            annual.loc[(annual["year"] == year) & (annual["geography"] == "rj_total")]
            .set_index("outcome_id")["count"]
            .to_dict()
        )
        for outcome_id, group in frame.groupby("outcome_id"):
            observed = int(group["count"].sum())
            target = int(expected.get(outcome_id, observed))
            if observed != target:
                reconciliation[outcome_id] = {"municipalTotal": observed, "annualSeriesTotal": target}
    reconciliation_status = "reconciled_with_annual_series" if not reconciliation else "reconciliation_failed"
    output = root / "data" / "processed" / f"sih_municipal_map_rates_{year}.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": reconciliation_status,
        "year": year, "municipalities": 92, "outcome_ids": list(QUERIES), "rows": len(frame),
        "suppressed_cells_lt_5": int((frame["count"] < 5).sum()),
        "reconciliation": reconciliation,
        "output_path": str(output.relative_to(root)), "output_sha256": sha256_file(output),
        "rules": {"residence": "SIH TabNet NR/RJ por município de residência", "rate": "AIHs / população residente × 100.000", "interval": "IC 95% exato de Poisson", "suppression": "count < 5 withheld before frontend"},
        "notes": ["Annual municipal snapshot aggregated from 12 monthly NR/RJ archives.", "An AIH is an event, not a unique person.", "No causal inference is produced."],
    }
    manifest_path = root / "reports" / "quality" / f"sih_municipal_map_{year}_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "reports" / "technical" / f"mapa_municipal_sih_{year}.md"
    report_path.write_text(
        f"# Camada municipal SIH {year}\n\n"
        f"A camada agrega 12 competências NR/RJ por município de residência para {len(QUERIES)} desfechos. "
        "AIHs são eventos de internação, não pessoas únicas. Células menores que cinco são suprimidas antes da publicação.\n"
        f"Reconciliação com a série agregada anual: **{reconciliation_status}**.\n"
        + (f"Divergências: `{json.dumps(reconciliation, ensure_ascii=False)}`\n" if reconciliation else ""),
        encoding="utf-8",
    )
    return output, manifest_path, report_path
