from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .config import project_root
from .download import download_public_file
from .logging_utils import configure_logging
from .provenance import sha256_file
from .raw_validation import write_raw_validation_report
from .sources import get_sample_source
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
                "Esta execução valida a estrutura, metadados e proveniência. "
                "Não calcula estimativas epidemiológicas.",
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
                "- O workspace inicial não continha dados ou documentação.",
                "- O endpoint FTP legado do SIH falhou na checagem de conectividade.",
                "- A reconciliação de totais oficiais ainda não foi executada.",
                "- Não há resultado negativo ou positivo sobre saúde de Volta Redonda nesta fase.",
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
    manifest = {
        "project": "vr_saude_ambiental",
        "code_version": __version__,
        "run_at": _utc_now(),
        "status": "preliminary_no_epidemiological_results",
        "inputs": [
            {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
            for path in tracked_inputs
        ],
        "outputs": [
            {"path": str(quality_report.relative_to(root)), "sha256": sha256_file(quality_report)},
        ],
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
    subparsers.add_parser("sources", help="list verified sample acquisition identifiers")
    acquire = subparsers.add_parser("acquire", help="download one public sample idempotently")
    acquire.add_argument("--source", required=True, help="sample source identifier")
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
    if args.command == "acquire":
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
        quality = _quality_report(root)
        manifest = _manifest(root, quality)
        print(f"Raw validation report: {raw_report}")
        print(f"Quality report: {quality}")
        print(f"Results manifest: {manifest}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
