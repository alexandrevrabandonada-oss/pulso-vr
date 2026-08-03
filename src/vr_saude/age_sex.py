from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .mortality import period_status
from .outcomes import AGE_GROUPS
from .provenance import sha256_file


PROFILE_OUTCOMES = [
    "all_malignant_neoplasms",
    "resp_all",
    "lung",
    "bladder",
    "non_hodgkin_lymphoma",
    "multiple_myeloma",
    "leukemia",
    "colorectal",
]
PROFILE_GEOGRAPHIES = ["volta_redonda", "rest_of_rj_excluding_vr"]


def profile_counts(counts: pd.DataFrame) -> pd.DataFrame:
    required = {
        "source_year",
        "geography",
        "outcome_id",
        "outcome_label",
        "age_group",
        "sex",
        "count",
    }
    missing = sorted(required - set(counts.columns))
    if missing:
        raise ValueError(f"SIM profile input is missing fields: {missing}")
    data = counts.copy()
    data["source_year"] = pd.to_numeric(data["source_year"], errors="raise").astype(int)
    data["count"] = pd.to_numeric(data["count"], errors="raise").astype(int)
    if (data["count"] < 0).any():
        raise ValueError("SIM profile counts contain negative values")
    keys = [
        "source_year",
        "geography",
        "outcome_id",
        "outcome_label",
        "age_group",
        "sex",
    ]
    profile = data.groupby(keys, as_index=False, dropna=False)["count"].sum()
    totals = (
        profile.groupby(["source_year", "geography", "outcome_id"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "total_count"})
    )
    profile = profile.merge(
        totals,
        on=["source_year", "geography", "outcome_id"],
        how="left",
        validate="many_to_one",
    )
    profile["share_pct"] = profile["count"] / profile["total_count"] * 100
    return profile


def _load_input(root: Path) -> tuple[pd.DataFrame, Path]:
    input_path = root / "data" / "processed" / "outcome_counts_sim_sivep.parquet"
    if not input_path.exists():
        raise FileNotFoundError(f"outcome counts Parquet is missing: {input_path}")
    counts = pd.read_parquet(input_path)
    counts = counts.loc[counts["source"] == "SIM"].copy()
    if counts.empty:
        raise ValueError("no SIM outcome counts available")
    return counts, input_path


def _write_report(root: Path, profile: pd.DataFrame, available_years: list[int]) -> Path:
    report = root / "reports" / "technical" / "perfil_etario_sexual_sim.md"
    display_years = [year for year in [2020, 2024] if year in available_years]
    selected = profile.loc[
        profile["year"].isin(display_years)
        & profile["outcome_id"].isin(PROFILE_OUTCOMES)
        & profile["geography"].isin(PROFILE_GEOGRAPHIES)
    ].copy()
    selected["age_order"] = selected["age_group"].map(
        {value: index for index, value in enumerate(AGE_GROUPS)}
    ).fillna(len(AGE_GROUPS))
    selected["sex_order"] = selected["sex"].map(
        {"masculino": 0, "feminino": 1, "ignorado": 2}
    ).fillna(3)
    rows = []
    for row in selected.sort_values(
        ["year", "outcome_id", "geography", "age_order", "sex_order"]
    ).itertuples(index=False):
        if row.count < 5:
            count = "<5"
            share = "<5"
        else:
            count = str(int(row.count))
            share = f"{row.share_pct:.2f}"
        rows.append(
            f"| {row.year} | {row.geography} | {row.outcome_id} | "
            f"{row.age_group} | {row.sex} | {count} | {share} |"
        )
    lines = [
        "# Perfil etário e sexual dos óbitos no SIM",
        "",
        f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Este produto descreve a distribuição dos óbitos de residentes por grupo "
        "etário amplo e sexo. A coluna de proporção é a participação dentro do "
        "desfecho, ano e território; não é uma taxa populacional.",
        "",
        f"- Anos disponíveis: **{available_years}**.",
        f"- Anos exibidos nesta tabela: **{display_years}**.",
        "- Este perfil é descritivo; as taxas específicas SIM 2022 usam denominadores "
        "separados e são publicadas em outro produto. Não há padronização neste perfil.",
        "- Células menores que cinco são exibidas como <5.",
        "",
        "## Perfil selecionado",
        "",
        "| ano | território | desfecho | idade | sexo | óbitos | % no desfecho |",
        "|---:|---|---|---|---|---:|---:|",
        *rows,
        "",
        "O Parquet contém todos os anos, desfechos e territórios disponíveis. "
        "A distribuição observada não deve ser interpretada como excesso de risco "
        "sem denominadores compatíveis, nem como causalidade ambiental ou ocupacional.",
        "",
        "## Regras e limitações",
        "",
        "- A idade do SIM é convertida de IDADE para grupos amplos; valores não interpretáveis ficam como ignorado.",
        "- O sexo usa SEXO=1 masculino e SEXO=2 feminino; demais valores ficam como ignorado.",
        "- A causa é a causa básica do óbito; causas múltiplas não entram nesta classificação.",
        "- O comparador é o restante do RJ excluindo Volta Redonda por residência.",
        "- 2020 permanece marcado como interrupção assistencial para câncer e pandemia para causas respiratórias.",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_age_sex_profile(root: Path) -> tuple[Path, Path, Path]:
    counts, input_path = _load_input(root)
    profile = profile_counts(counts)
    available_years = sorted(profile["source_year"].unique().tolist())
    period_map = {
        (int(year), outcome_id): period_status(root, int(year), outcome_id)
        for year, outcome_id in profile[["source_year", "outcome_id"]].drop_duplicates().itertuples(
            index=False,
            name=None,
        )
    }
    profile["period_status"] = [
        period_map[(int(year), outcome_id)]
        for year, outcome_id in zip(profile["source_year"], profile["outcome_id"])
    ]
    profile = profile.rename(columns={"source_year": "year"})
    profile = profile.sort_values(
        ["year", "outcome_id", "geography", "age_group", "sex"]
    ).reset_index(drop=True)
    output = root / "data" / "processed" / "sim_mortality_age_sex_profile.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    profile.to_parquet(output, index=False)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "descriptive_sim_age_sex_profile_no_specific_rates",
        "rows": int(len(profile)),
        "available_years": available_years,
        "outcome_ids": sorted(profile["outcome_id"].unique().tolist()),
        "geographies": sorted(profile["geography"].unique().tolist()),
        "output_path": str(output.relative_to(root)),
        "output_sha256": sha256_file(output),
        "input_files": [
            {"path": str(input_path.relative_to(root)), "sha256": sha256_file(input_path)}
        ],
        "rules": {
            "age_groups": AGE_GROUPS,
            "sex_mapping": {"1": "masculino", "2": "feminino", "other": "ignorado"},
            "unit": "óbitos de residentes; causa básica do SIM",
            "share": "count divided by total count within year, geography and outcome",
        },
        "notes": [
            "The profile is descriptive and does not produce age-specific rates.",
            "No age-sex denominators or direct standardization are available in this step.",
            "Small cells are suppressed in the technical report.",
            "SIM deaths are not incident cancer cases and no causal inference is produced.",
        ],
    }
    manifest_path = root / "reports" / "quality" / "sim_age_sex_profile_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = _write_report(root, profile, available_years)
    return output, manifest_path, report_path
