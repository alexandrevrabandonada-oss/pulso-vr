from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .provenance import sha256_file

OUTCOMES = {"alzheimer", "dementias_all"}
REQUIRED_COLUMNS = {"year", "municipality_code_ibge", "outcome_id", "count"}


def build_sia_alzheimer_production(root: Path) -> tuple[Path | None, Path, Path]:
    """Validate an explicitly diagnostic SIA extract without inventing residence.

    The current public SIA TabNet tables are establishment-based. The adapter
    therefore consumes only a harmonized extract that explicitly carries a
    validated CID dimension. If it is absent, the result is recorded as
    unavailable instead of publishing a proxy based on procedures.
    """
    input_path = root / "data" / "interim" / "sia_diagnostic_production.csv"
    manifest_path = root / "reports" / "quality" / "sia_alzheimer_manifest.json"
    report_path = root / "reports" / "technical" / "sia_alzheimer.md"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not input_path.exists():
        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "unavailable_no_validated_diagnostic_dimension",
            "input_path": str(input_path.relative_to(root)),
            "geography_basis": "establishment",
            "measure": "ambulatory_production",
            "outcome_ids": sorted(OUTCOMES),
            "notes": [
                "No SIA extract with a validated CID-10 diagnostic dimension was found.",
                "Procedure counts are not substituted for Alzheimer/dementia diagnoses.",
                "No residence-based disease rate is calculated from SIA.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report_path.write_text(
            "# SIA — Alzheimer e demências\n\n"
            "Indisponível nesta versão: a produção ambulatorial não será publicada até que exista "
            "uma dimensão diagnóstica CID-10 validada. O município do estabelecimento não substitui "
            "o município de residência.\n",
            encoding="utf-8",
        )
        return None, manifest_path, report_path

    frame = pd.read_csv(input_path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"SIA diagnostic extract is missing columns: {missing}")
    if "geography_basis" not in frame.columns or set(frame["geography_basis"].dropna().unique()) != {"establishment"}:
        raise ValueError("SIA production must declare geography_basis=establishment")
    frame = frame.loc[frame["outcome_id"].isin(OUTCOMES)].copy()
    frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype(int)
    frame["count"] = pd.to_numeric(frame["count"], errors="raise").astype(int)
    if (frame["count"] < 0).any():
        raise ValueError("SIA production contains negative counts")
    frame["outcome_label"] = frame["outcome_id"].map({
        "alzheimer": "Doença de Alzheimer",
        "dementias_all": "Doença de Alzheimer e outras demências",
    })
    frame["period_status"] = frame["year"].map(lambda year: "provisional" if year >= 2025 else "source_year_observed")
    frame["geography"] = frame["municipality_code_ibge"].astype(str).str.zfill(7)
    frame = frame.groupby(["year", "geography", "outcome_id", "outcome_label", "geography_basis"], as_index=False)["count"].sum()
    output = root / "data" / "processed" / "sia_alzheimer_production.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "validated_sia_diagnostic_production_establishment",
        "rows": int(len(frame)),
        "outcome_ids": sorted(frame["outcome_id"].unique().tolist()),
        "input_file": {"path": str(input_path.relative_to(root)), "sha256": sha256_file(input_path)},
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "rules": {
            "geography": "municipality where the ambulatory establishment is located",
            "measure": "production count; no resident denominator",
            "suppression": "small cells are suppressed before public publication",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        "# SIA — Alzheimer e demências\n\n"
        "Produção ambulatorial por município do estabelecimento. Esta camada é assistencial e "
        "não é uma taxa de residentes, prevalência ou incidência.\n",
        encoding="utf-8",
    )
    return output, manifest_path, report_path
