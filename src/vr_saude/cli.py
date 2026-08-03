from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .age_sex_rates import build_age_sex_rates
from .config import project_root
from .download import download_public_file
from .discovery import discover_resources, select_resource
from .age_sex import build_age_sex_profile
from .harmonize import harmonize_sources
from .interrupted_respiratory import build_interrupted_respiratory
from .logging_utils import configure_logging
from .layout_validation import write_layout_manifest
from .mortality import build_mortality_rates
from .oncology_diagnoses import build_oncology_diagnoses
from .outcomes import build_outcome_counts
from .population import acquire_population, harmonize_population
from .population_age_sex import acquire_age_sex_population, harmonize_age_sex_population
from .portal_data import build_portal_data
from .portal_release import write_portal_preflight
from .provenance import sha256_file
from .raw_validation import write_raw_validation_report
from .rates import build_respiratory_rates
from .reporting import write_respiratory_report
from .sih_morbidity import query_morbidity_series, query_national_morbidity_series
from .sih_municipal_map import build_sih_municipal_map
from .sih_tabnet import query_residence, query_residence_series, save_query_response, write_harmonized_series
from .sim_municipal_map import build_sim_municipal_map
from .sources import get_sample_source
from .surveillance import build_sivep_surveillance_summary
from .sivep_monthly import build_sivep_monthly
from .territory_validation import write_territory_report
from .validate import validate_project


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _quality_report(root: Path) -> Path:
    log_path = root / "metadata" / "extraction_log.csv"
    rows = []
    with log_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    raw_files = [
        path for path in (root / "data" / "raw").iterdir()
        if path.is_file() and path.name not in {"README.md", ".gitkeep"} and not path.name.endswith(".sha256")
    ]
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("status", "") or "empty"
        status_counts[status] = status_counts.get(status, 0) + 1
    report = root / "reports" / "quality" / "quality_report_initial.md"
    report.write_text(
        "\n".join(
            [
                "# Relatório inicial de qualidade",
                "",
                f"Execução: {_utc_now()}",
                "",
                "## Escopo",
                "",
                "Esta execução valida a estrutura, metadados, proveniência e "
                "amostras iniciais. Não calcula estimativas epidemiológicas.",
                "",
                "## Arquivos brutos",
                "",
                f"Arquivos brutos não auxiliares encontrados: **{len(raw_files)}**.",
                "Todos os arquivos brutos presentes devem ter sidecar `.sha256`.",
                "",
                "## Log de extração",
                "",
                f"Entradas no log: **{len(rows)}**.",
                f"Contagem por status: `{json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}`.",
                "",
                "## Achados e limites",
                "",
                "- O workspace inicial não continha dados ou documentação; a Fase 2 agora possui amostras oficiais versionadas por hash.",
                "- O endpoint FTP legado do SIH falhou na checagem de conectividade, mas a rota TabNet por residência foi executada para 221 competências entre 2008 e maio de 2026.",
                "- O catálogo dinâmico de recursos SIM/SIVEP e os layouts observados foram preservados em metadata/.",
                "- A série SIH harmonizada em data/interim/ é descritiva e mantém o vínculo com cada resposta HTML bruta.",
                "- A reconciliação de totais oficiais ainda não foi executada.",
                "- Há resultados preliminares descritivos, mas nenhuma hipótese causal ou etiológica foi confirmada.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def _manifest(root: Path, quality_report: Path) -> Path:
    tracked_inputs = [
        root / "config" / "outcomes.yml",
        root / "config" / "periods.yml",
        root / "config" / "sources.yml",
        root / "config" / "territories.yml",
        root / "metadata" / "source_catalog.csv",
        root / "metadata" / "extraction_log.csv",
    ]
    generated_outputs = [
        quality_report,
        root / "reports" / "quality" / "raw_samples_validation.md",
        root / "reports" / "quality" / "raw_samples_validation.json",
        root / "reports" / "quality" / "territory_code_validation.md",
        root / "reports" / "quality" / "territory_code_validation.json",
        root / "metadata" / "layout_manifest.json",
        root / "metadata" / "discovered_resources_sim.json",
        root / "metadata" / "discovered_resources_sivep.json",
        root / "reports" / "quality" / "harmonization_manifest.json",
        root / "reports" / "quality" / "population_denominator_manifest.json",
        root / "reports" / "quality" / "population_age_sex_manifest.json",
        root / "reports" / "quality" / "respiratory_rates_manifest.json",
        root / "reports" / "quality" / "respiratory_its_manifest.json",
        root / "reports" / "quality" / "outcome_counts_manifest.json",
        root / "reports" / "quality" / "sivep_surveillance_manifest.json",
        root / "reports" / "quality" / "sivep_monthly_manifest.json",
        root / "reports" / "quality" / "sim_mortality_rates_manifest.json",
        root / "reports" / "quality" / "sim_age_sex_profile_manifest.json",
        root / "reports" / "quality" / "sim_age_sex_rates_manifest.json",
        root / "reports" / "quality" / "sim_municipal_map_2022_manifest.json",
        root / "reports" / "quality" / "sih_municipal_map_2022_manifest.json",
        root / "reports" / "quality" / "portal_accessibility_audit.json",
        root / "reports" / "technical" / "fase3_respiratorio.md",
        root / "reports" / "technical" / "denominadores.md",
        root / "reports" / "technical" / "denominadores_idade_sexo_2022.md",
        root / "reports" / "technical" / "taxas_respiratorias.md",
        root / "reports" / "technical" / "serie_interrompida_respiratoria.md",
        root / "reports" / "technical" / "desfechos_sim_sivep.md",
        root / "reports" / "technical" / "pandemia_sivep.md",
        root / "reports" / "technical" / "sivep_mensal.md",
        root / "reports" / "technical" / "mortalidade_sim.md",
        root / "reports" / "technical" / "perfil_etario_sexual_sim.md",
        root / "reports" / "technical" / "taxas_sim_idade_sexo_2022.md",
        root / "reports" / "technical" / "mapa_municipal_sim_2022.md",
        root / "reports" / "technical" / "mapa_municipal_sih_2022.md",
        root / "reports" / "reviews" / "epidemiology_review_draft.md",
        root / "reports" / "reviews" / "accessibility_review_draft.md",
        root / "reports" / "technical" / "diagnosticos_painel_oncologia.md",
        root / "reports" / "technical" / "territorialidade_cancer_bairros.md",
        root / "reports" / "quality" / "painel_oncologia_diagnoses_manifest.json",
    ] + sorted((root / "reports" / "quality").glob("sih_series_*.json")) + sorted(
        (root / "reports" / "quality").glob("sih_morbidity_*.json")
    )
    raw_samples = [
        {
            "path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted((root / "data" / "raw").iterdir())
        if path.is_file() and not path.name.endswith(".sha256") and path.name not in {"README.md", ".gitkeep"}
    ]
    derived_artifact_paths = [
        *sorted((root / "data" / "interim").iterdir()),
        *sorted((root / "data" / "processed").iterdir()),
    ]
    derived_artifacts = [
        {
            "path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in derived_artifact_paths
        if path.is_file() and path.name not in {"README.md", ".gitkeep"}
    ]
    manifest = {
        "project": "vr_saude_ambiental",
        "code_version": __version__,
        "run_at": _utc_now(),
        "status": "preliminary_descriptive_analyses_no_causal_inference",
        "inputs": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in tracked_inputs
        ],
        "outputs": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in generated_outputs
            if path.exists()
        ],
        "raw_samples": raw_samples,
        "derived_artifacts": derived_artifacts,
        "results": [],
        "notes": [
            "No causal conclusion is authorized by this run.",
            "Volta Redonda is excluded from the primary RJ comparator by config/territories.yml.",
            "Raw data remain outside version control unless explicitly approved.",
        ],
    }
    destination = root / "outputs" / "results_manifest.json"
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vr-saude", description="Pipeline vr_saude_ambiental")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate project structure and configurations")
    subparsers.add_parser("all", help="validate and build initial quality/manifest artifacts")
    subparsers.add_parser("validate-raw", help="validate hashes and structural integrity of raw samples")
    subparsers.add_parser("validate-layout", help="validate source-specific layouts of raw samples")
    subparsers.add_parser("validate-territories", help="validate residence codes for Volta Redonda")
    harmonize = subparsers.add_parser("harmonize", help="create interim named-field Parquet outputs")
    harmonize.add_argument("--source", choices=("all", "sim", "sivep"), default="all")
    harmonize.add_argument("--year", type=int, action="append", help="harmonize only this year; repeatable")
    sih_query = subparsers.add_parser("sih-query", help="query one official SIH TabNet month by residence")
    sih_query.add_argument("--year", type=int, default=2024)
    sih_query.add_argument("--month", type=int, default=1)
    sih_series = subparsers.add_parser("sih-series", help="query and harmonize a monthly SIH TabNet range")
    sih_series.add_argument("--start-year", type=int, required=True)
    sih_series.add_argument("--start-month", type=int, required=True)
    sih_series.add_argument("--end-year", type=int, required=True)
    sih_series.add_argument("--end-month", type=int, required=True)
    sih_morbidity = subparsers.add_parser(
        "sih-morbidity",
        help="query official SIH respiratory morbidity groups by residence",
    )
    sih_morbidity.add_argument("--start-year", type=int, required=True)
    sih_morbidity.add_argument("--start-month", type=int, required=True)
    sih_morbidity.add_argument("--end-year", type=int, required=True)
    sih_morbidity.add_argument("--end-month", type=int, required=True)
    sih_morbidity.add_argument("--workers", type=int, default=2)
    sih_national = subparsers.add_parser(
        "sih-national-morbidity",
        help="query the official Brazil-total SIH morbidity table by residence",
    )
    sih_national.add_argument("--start-year", type=int, required=True)
    sih_national.add_argument("--start-month", type=int, required=True)
    sih_national.add_argument("--end-year", type=int, required=True)
    sih_national.add_argument("--end-month", type=int, required=True)
    sih_national.add_argument("--workers", type=int, default=2)
    subparsers.add_parser(
        "respiratory-report",
        help="write the reproducible descriptive SIH respiratory report",
    )
    population_acquire = subparsers.add_parser(
        "population-acquire",
        help="download official SIDRA population denominator payloads",
    )
    population_acquire.add_argument("--start-year", type=int, default=2008)
    population_acquire.add_argument("--end-year", type=int, default=2025)
    population_harmonize = subparsers.add_parser(
        "population-harmonize",
        help="filter SIDRA payloads to RJ and create denominator Parquet outputs",
    )
    population_harmonize.add_argument("--start-year", type=int, default=2008)
    population_harmonize.add_argument("--end-year", type=int, default=2025)
    population_age_sex_acquire = subparsers.add_parser(
        "population-age-sex-acquire",
        help="download SIDRA 9514 Census 2022 age-sex payloads for RJ",
    )
    population_age_sex_acquire.add_argument("--chunk-size", type=int, default=20)
    subparsers.add_parser(
        "population-age-sex-harmonize",
        help="harmonize SIDRA 9514 Census 2022 age-sex denominators",
    )
    subparsers.add_parser(
        "respiratory-rates",
        help="calculate crude annual respiratory rates with exact Poisson intervals",
    )
    subparsers.add_parser(
        "respiratory-its",
        help="fit a descriptive interrupted time series at March 2020",
    )
    subparsers.add_parser(
        "outcome-counts",
        help="classify SIM CID-10 and SIVEP outcomes by residence",
    )
    subparsers.add_parser(
        "sivep-summary",
        help="summarize SIVEP notifications, notification rates and deaths",
    )
    subparsers.add_parser(
        "sivep-monthly",
        help="aggregate SIVEP monthly notifications by symptom onset and residence",
    )
    subparsers.add_parser(
        "sim-mortality-rates",
        help="calculate sampled SIM crude mortality rates with Poisson intervals",
    )
    subparsers.add_parser(
        "sim-age-sex-profile",
        help="describe SIM deaths by broad age group and sex",
    )
    subparsers.add_parser(
        "sim-age-sex-rates",
        help="calculate SIM 2022 specific crude rates by age group and sex",
    )
    subparsers.add_parser(
        "sim-municipal-map",
        help="calculate validated SIM 2022 municipal residence rates for the RJ map",
    )
    sih_municipal_map = subparsers.add_parser(
        "sih-municipal-map",
        help="query validated SIH annual municipal residence rates for the RJ map",
    )
    sih_municipal_map.add_argument("--year", type=int, default=2022)
    sih_municipal_map.add_argument("--workers", type=int, default=4)
    subparsers.add_parser(
        "oncology-diagnoses",
        help="harmonize Painel-Oncologia registered diagnoses by residence",
    )
    portal_data = subparsers.add_parser(
        "portal-data",
        help="publish privacy-safe static JSON/TopoJSON artifacts for the portal",
    )
    portal_data.add_argument("--release-id", default="technical-beta")
    portal_data.add_argument(
        "--acquire-geography",
        action="store_true",
        help="download the official IBGE RJ municipality mesh when it is absent",
    )
    portal_preflight = subparsers.add_parser(
        "portal-preflight",
        help="audit portal artifacts and write the public-release readiness report",
    )
    portal_preflight.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero while any blocker remains",
    )
    discover = subparsers.add_parser("discover", help="save the current official resource catalog")
    discover.add_argument("--dataset", choices=("sim", "sivep"), required=True)
    subparsers.add_parser("sources", help="list verified sample acquisition identifiers")
    acquire = subparsers.add_parser("acquire", help="download one public sample idempotently")
    acquire.add_argument("--source", help="sample source identifier")
    acquire.add_argument("--dataset", choices=("sim", "sivep"), help="discover a year-specific resource")
    acquire.add_argument("--year", type=int, help="year for dynamic official resource discovery")
    return parser


def main(argv: list[str] | None = None) -> int:
    root = project_root()
    args = _parser().parse_args(argv)
    logger = configure_logging(root)
    if args.command == "sources":
        for source_id in sorted(__import__("vr_saude.download", fromlist=["SAMPLE_SOURCES"]).SAMPLE_SOURCES):
            print(source_id)
        return 0
    if args.command == "validate":
        issues = validate_project(root)
        if issues:
            for issue in issues:
                print(f"ERROR: {issue}", file=sys.stderr)
            return 1
        print("Validation passed")
        return 0
    if args.command == "validate-raw":
        _, report, results = write_raw_validation_report(root)
        failed = [item for item in results if not item["ok"]]
        print(f"Raw validation report: {report}")
        if failed:
            for item in failed:
                print(f"ERROR: {item['filename']}: {item['errors']}", file=sys.stderr)
            return 1
        print(f"Raw samples validated: {len(results)}")
        return 0
    if args.command == "validate-layout":
        report, results = write_layout_manifest(root)
        failed = [item for item in results if not item["ok"]]
        print(f"Layout manifest: {report}")
        if failed:
            for item in failed:
                print(f"ERROR: {item['path']}: {item['errors']}", file=sys.stderr)
            return 1
        print(f"Layouts validated: {len(results)}")
        return 0
    if args.command == "validate-territories":
        json_report, md_report, results = write_territory_report(root)
        failed = [item for item in results if not item["ok"]]
        print(f"Territory JSON report: {json_report}")
        print(f"Territory Markdown report: {md_report}")
        if failed:
            for item in failed:
                print(f"ERROR: {item['path']}: {item['errors']}", file=sys.stderr)
            return 1
        print(f"Territory samples validated: {len(results)}")
        return 0
    if args.command == "harmonize":
        try:
            report, results = harmonize_sources(
                root,
                args.source,
                years=set(args.year) if args.year else None,
            )
        except (ValueError, OSError, TypeError) as exc:
            print(f"ERROR: harmonization failed: {exc}", file=sys.stderr)
            return 1
        print(f"Harmonization manifest: {report}")
        for item in results:
            print(
                f"{item['source']} {item['source_year']}: "
                f"{item['rows']} rows, {item['residence_vr_rows']} VR residents -> {item['output_path']}"
            )
        return 0
    if args.command == "sih-query":
        try:
            result = query_residence(root, args.year, args.month)
            destination = save_query_response(root, result)
        except (LookupError, ValueError, OSError) as exc:
            print(f"ERROR: SIH TabNet query failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIH TabNet response: {destination}")
        print(f"Volta Redonda / {args.year:04d}-{args.month:02d}: {result.hospitalizations} internações")
        return 0
    if args.command == "sih-series":
        try:
            results = query_residence_series(
                root,
                args.start_year,
                args.start_month,
                args.end_year,
                args.end_month,
            )
            for result in results:
                save_query_response(root, result)
            interim, report = write_harmonized_series(root, results)
        except (LookupError, ValueError, OSError) as exc:
            print(f"ERROR: SIH TabNet series failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIH raw responses: {len(results)}")
        print(f"Harmonized interim series: {interim}")
        print(f"Series quality report: {report}")
        print(f"Aggregated events: {sum(item.hospitalizations for item in results)}")
        return 0
    if args.command == "sih-morbidity":
        try:
            interim, report = query_morbidity_series(
                root,
                args.start_year,
                args.start_month,
                args.end_year,
                args.end_month,
                workers=args.workers,
            )
        except (LookupError, ValueError, OSError) as exc:
            print(f"ERROR: SIH morbidity query failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIH morbidity interim series: {interim}")
        print(f"Morbidity quality report: {report}")
        return 0
    if args.command == "sih-national-morbidity":
        try:
            interim, report = query_national_morbidity_series(
                root,
                args.start_year,
                args.start_month,
                args.end_year,
                args.end_month,
                workers=args.workers,
            )
        except (LookupError, ValueError, OSError) as exc:
            print(f"ERROR: SIH Brazil morbidity query failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIH Brazil morbidity interim series: {interim}")
        print(f"Brazil morbidity quality report: {report}")
        return 0
    if args.command == "respiratory-report":
        try:
            report = write_respiratory_report(root)
        except (OSError, ValueError) as exc:
            print(f"ERROR: respiratory report failed: {exc}", file=sys.stderr)
            return 1
        print(f"Respiratory report: {report}")
        return 0
    if args.command == "population-acquire":
        try:
            paths = acquire_population(root, args.start_year, args.end_year)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"ERROR: population acquisition failed: {exc}", file=sys.stderr)
            return 1
        print(f"Population raw payloads: {len(paths)}")
        for path in paths:
            print(path)
        return 0
    if args.command == "population-harmonize":
        try:
            municipality, denominator, report = harmonize_population(
                root,
                args.start_year,
                args.end_year,
            )
        except (OSError, ValueError, TypeError) as exc:
            print(f"ERROR: population harmonization failed: {exc}", file=sys.stderr)
            return 1
        print(f"Population municipality Parquet: {municipality}")
        print(f"Population denominator Parquet: {denominator}")
        print(f"Population report: {report}")
        return 0
    if args.command == "population-age-sex-acquire":
        try:
            paths = acquire_age_sex_population(root, chunk_size=args.chunk_size)
        except (OSError, ValueError, RuntimeError, FileNotFoundError) as exc:
            print(f"ERROR: age-sex population acquisition failed: {exc}", file=sys.stderr)
            return 1
        print(f"Age-sex population raw payloads: {len(paths)}")
        for path in paths:
            print(path)
        return 0
    if args.command == "population-age-sex-harmonize":
        try:
            municipality, denominator, report = harmonize_age_sex_population(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: age-sex population harmonization failed: {exc}", file=sys.stderr)
            return 1
        print(f"Age-sex municipality Parquet: {municipality}")
        print(f"Age-sex denominator Parquet: {denominator}")
        print(f"Age-sex population report: {report}")
        return 0
    if args.command == "respiratory-rates":
        try:
            output, manifest, report = build_respiratory_rates(root)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(f"ERROR: respiratory rates failed: {exc}", file=sys.stderr)
            return 1
        print(f"Respiratory rates Parquet: {output}")
        print(f"Respiratory rates manifest: {manifest}")
        print(f"Respiratory rates report: {report}")
        return 0
    if args.command == "respiratory-its":
        try:
            output, manifest, report = build_interrupted_respiratory(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: respiratory interrupted series failed: {exc}", file=sys.stderr)
            return 1
        print(f"Respiratory interrupted series Parquet: {output}")
        print(f"Respiratory interrupted series manifest: {manifest}")
        print(f"Respiratory interrupted series report: {report}")
        return 0
    if args.command == "outcome-counts":
        try:
            output, manifest, report = build_outcome_counts(root)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(f"ERROR: outcome classification failed: {exc}", file=sys.stderr)
            return 1
        print(f"Outcome counts Parquet: {output}")
        print(f"Outcome counts manifest: {manifest}")
        print(f"Outcome counts report: {report}")
        return 0
    if args.command == "sivep-summary":
        try:
            output, manifest, report = build_sivep_surveillance_summary(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: SIVEP surveillance summary failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIVEP surveillance Parquet: {output}")
        print(f"SIVEP surveillance manifest: {manifest}")
        print(f"SIVEP surveillance report: {report}")
        return 0
    if args.command == "sivep-monthly":
        try:
            output, manifest, report = build_sivep_monthly(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: SIVEP monthly series failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIVEP monthly Parquet: {output}")
        print(f"SIVEP monthly manifest: {manifest}")
        print(f"SIVEP monthly report: {report}")
        return 0
    if args.command == "sim-mortality-rates":
        try:
            output, manifest, report = build_mortality_rates(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: SIM mortality rates failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIM mortality rates Parquet: {output}")
        print(f"SIM mortality rates manifest: {manifest}")
        print(f"SIM mortality rates report: {report}")
        return 0
    if args.command == "sim-age-sex-profile":
        try:
            output, manifest, report = build_age_sex_profile(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: SIM age-sex profile failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIM age-sex profile Parquet: {output}")
        print(f"SIM age-sex profile manifest: {manifest}")
        print(f"SIM age-sex profile report: {report}")
        return 0
    if args.command == "sim-age-sex-rates":
        try:
            output, manifest, report = build_age_sex_rates(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: SIM age-sex rates failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIM age-sex rates Parquet: {output}")
        print(f"SIM age-sex rates manifest: {manifest}")
        print(f"SIM age-sex rates report: {report}")
        return 0
    if args.command == "sim-municipal-map":
        try:
            output, manifest, report = build_sim_municipal_map(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: SIM municipal map failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIM municipal map Parquet: {output}")
        print(f"SIM municipal map manifest: {manifest}")
        print(f"SIM municipal map report: {report}")
        return 0
    if args.command == "sih-municipal-map":
        try:
            output, manifest, report = build_sih_municipal_map(root, year=args.year, workers=args.workers)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: SIH municipal map failed: {exc}", file=sys.stderr)
            return 1
        print(f"SIH municipal map Parquet: {output}")
        print(f"SIH municipal map manifest: {manifest}")
        print(f"SIH municipal map report: {report}")
        return 0
    if args.command == "oncology-diagnoses":
        try:
            output, manifest, report = build_oncology_diagnoses(root)
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: oncology diagnoses failed: {exc}", file=sys.stderr)
            return 1
        print(f"Oncology diagnoses Parquet: {output}")
        print(f"Oncology diagnoses manifest: {manifest}")
        print(f"Oncology diagnoses report: {report}")
        return 0
    if args.command == "portal-data":
        try:
            output, release = build_portal_data(
                root,
                release_id=args.release_id,
                acquire_geography=args.acquire_geography,
            )
        except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
            print(f"ERROR: portal data publication failed: {exc}", file=sys.stderr)
            return 1
        print(f"Portal data directory: {output}")
        print(f"Portal release manifest: {release}")
        return 0
    if args.command == "portal-preflight":
        try:
            quality, technical, report = write_portal_preflight(root)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            print(f"ERROR: portal preflight failed: {exc}", file=sys.stderr)
            return 1
        print(f"Portal preflight JSON: {quality}")
        print(f"Portal launch report: {technical}")
        print(
            f"Portal readiness: {report['status']} "
            f"({report['summary']['blockerCount']} blockers, "
            f"{report['summary']['warningCount']} warnings)"
        )
        if args.strict and not report["publicationAllowed"]:
            return 1
        return 0
    if args.command == "discover":
        resources = discover_resources(args.dataset)
        destination = root / "metadata" / f"discovered_resources_{args.dataset}.json"
        destination.write_text(json.dumps(resources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Discovered {len(resources)} resources: {destination}")
        return 0
    if args.command == "acquire":
        if args.dataset and args.year is not None:
            resources = discover_resources(args.dataset)
            resource = select_resource(resources, args.year)
            url = resource["url"]
            filename = f"{args.dataset}_{args.year}_{Path(url.split('?', 1)[0]).name}"
            path = download_public_file(
                root,
                source_id=f"{args.dataset}_discovered_{args.year}",
                url=url,
                filename=filename,
                period=str(args.year),
                territory="RJ",
                logger=logger,
            )
            print(path)
            return 0
        if not args.source:
            print("--source is required unless --dataset and --year are provided", file=sys.stderr)
            return 2
        spec = get_sample_source(args.source)
        try:
            path = download_public_file(
                root,
                source_id=args.source,
                url=spec["url"],
                filename=spec["filename"],
                period=spec["period"],
                territory=spec["territory"],
                logger=logger,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(path)
        return 0
    if args.command == "all":
        issues = validate_project(root)
        if issues:
            for issue in issues:
                print(f"ERROR: {issue}", file=sys.stderr)
            return 1
        _, raw_report, raw_results = write_raw_validation_report(root)
        raw_failures = [item for item in raw_results if not item["ok"]]
        if raw_failures:
            for item in raw_failures:
                print(f"ERROR: raw sample {item['filename']}: {item['errors']}", file=sys.stderr)
            return 1
        _, layout_results = write_layout_manifest(root)
        layout_failures = [item for item in layout_results if not item["ok"]]
        if layout_failures:
            for item in layout_failures:
                print(f"ERROR: raw layout {item['path']}: {item['errors']}", file=sys.stderr)
            return 1
        _, _, territory_results = write_territory_report(root)
        territory_failures = [item for item in territory_results if not item["ok"]]
        if territory_failures:
            for item in territory_failures:
                print(f"ERROR: territory validation {item['path']}: {item['errors']}", file=sys.stderr)
            return 1
        quality = _quality_report(root)
        respiratory_report = None
        if list((root / "data" / "interim").glob("sih_morbidity_*.csv")):
            respiratory_report = write_respiratory_report(root)
        if (
            respiratory_report
            and (root / "data" / "processed" / "population_denominators.parquet").exists()
        ):
            try:
                _, _, respiratory_its_report = build_interrupted_respiratory(root)
            except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
                print(f"ERROR: respiratory interrupted series failed: {exc}", file=sys.stderr)
                return 1
        else:
            respiratory_its_report = None
        oncology_report = None
        if all(
            (root / "data" / "raw" / filename).exists()
            for filename in (
                "painel_oncologia_vr_2013_2024.csv",
                "painel_oncologia_rj_2013_2024.csv",
                "painel_oncologia_brasil_2013_2024.csv",
                "painel_oncologia_vr_detalhado_2024.csv",
            )
        ):
            try:
                _, _, oncology_report = build_oncology_diagnoses(root)
            except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as exc:
                print(f"ERROR: oncology diagnoses failed: {exc}", file=sys.stderr)
                return 1
        manifest = _manifest(root, quality)
        print(f"Raw validation report: {raw_report}")
        print(f"Quality report: {quality}")
        if respiratory_report:
            print(f"Respiratory report: {respiratory_report}")
        if respiratory_its_report:
            print(f"Respiratory interrupted series report: {respiratory_its_report}")
        if oncology_report:
            print(f"Oncology diagnoses report: {oncology_report}")
        print(f"Results manifest: {manifest}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
