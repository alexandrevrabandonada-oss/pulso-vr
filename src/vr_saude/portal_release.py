from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_OBSERVATION_FIELDS = {
    "source",
    "outcomeId",
    "geographyId",
    "period",
    "metricKind",
    "value",
    "count",
    "denominator",
    "ciLow",
    "ciHigh",
    "dataStatus",
    "periodStatus",
    "suppressed",
    "manifestRef",
}
BRAZIL_GEOGRAPHY = "brazil_total"
REQUIRED_PROFILE_FIELDS = {
    "municipalityCode", "indicatorId", "period", "ageGroup", "sex", "count",
    "denominator", "ratePer100k", "ciLow", "ciHigh", "suppressionStatus",
    "dataStatus", "manifestRef",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finding(
    finding_id: str,
    severity: str,
    title: str,
    detail: str,
    action: str,
) -> dict[str, str]:
    return {
        "id": finding_id,
        "severity": severity,
        "title": title,
        "detail": detail,
        "action": action,
    }


def assess_portal_release(root: Path) -> dict[str, Any]:
    """Audit the static portal package without exposing raw or personal data."""

    output_root = root / "site" / "public" / "data"
    release_path = output_root / "release.json"
    catalog_path = output_root / "catalog.json"
    release = _read_json(release_path)
    catalog = _read_json(catalog_path)
    indicators = catalog.get("indicators", [])

    findings: list[dict[str, str]] = []
    series_files = 0
    profile_files = 0
    map_files = 0
    profile_observations = 0
    map_values = 0
    map_suppressed = 0
    observations = 0
    suppressed = 0
    unsuppressed_small_cells: list[dict[str, Any]] = []
    schema_missing: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    download_suppression_leaks: list[dict[str, Any]] = []
    profile_suppression_leaks: list[dict[str, Any]] = []
    profile_municipality_codes: set[str] = set()
    indicators_without_profiles: list[str] = []
    profile_eligible_indicators: list[str] = []
    indicators_without_maps: list[str] = []
    sih_indicators = 0
    sih_with_brazil = 0
    map_status_counts: dict[str, int] = {}

    for indicator in indicators:
        indicator_id = indicator["id"]
        series_path = output_root / "series" / f"{indicator_id}.json"
        profile_path = output_root / "profiles" / f"{indicator_id}.json"
        map_path = output_root / "maps" / "rj" / f"{indicator_id}.json"

        if series_path.exists():
            series_files += 1
            series_payload = _read_json(series_path)
            series_observations = series_payload.get("observations", [])
            has_brazil = False
            for observation in series_observations:
                observations += 1
                missing = sorted(REQUIRED_OBSERVATION_FIELDS - observation.keys())
                if missing:
                    schema_missing.append({"indicatorId": indicator_id, "missing": missing})
                count = observation.get("count")
                if observation.get("suppressed"):
                    suppressed += 1
                if count is not None and int(count) < 5 and not observation.get("suppressed"):
                    unsuppressed_small_cells.append(
                        {
                            "indicatorId": indicator_id,
                            "geographyId": observation.get("geographyId"),
                            "period": observation.get("period"),
                            "count": count,
                        }
                    )
                source = str(observation.get("source", "unknown"))
                source_counts[source] = source_counts.get(source, 0) + 1
                data_status = str(observation.get("dataStatus", "unknown"))
                status_counts[data_status] = status_counts.get(data_status, 0) + 1
                has_brazil = has_brazil or observation.get("geographyId") == BRAZIL_GEOGRAPHY
            if indicator.get("source") == "SIH":
                sih_indicators += 1
                if has_brazil:
                    sih_with_brazil += 1
        else:
            schema_missing.append({"indicatorId": indicator_id, "missing": ["seriesFile"]})

        profile_required = indicator.get("profileAvailability") == "available_2022_sim_age_sex" or indicator.get("source") == "SIM"
        if profile_required:
            profile_eligible_indicators.append(indicator_id)

        if profile_path.exists():
            profile_files += 1
            profile_payload = _read_json(profile_path)
            count = len(profile_payload.get("observations", []))
            profile_observations += count
            statewide_profile = indicator.get("profileCoverage", {}).get("status") == "available"
            for observation in profile_payload.get("observations", []) if statewide_profile else []:
                missing = sorted(REQUIRED_PROFILE_FIELDS - observation.keys())
                if missing:
                    schema_missing.append({"indicatorId": indicator_id, "profileMissing": missing})
                code = observation.get("municipalityCode")
                if code:
                    profile_municipality_codes.add(str(code))
                if observation.get("suppressionStatus") == "suppressed":
                    leaked = [field for field in ("count", "ratePer100k", "ciLow", "ciHigh") if observation.get(field) is not None]
                    if leaked:
                        profile_suppression_leaks.append({"indicatorId": indicator_id, "municipalityCode": code, "fields": leaked})
            if profile_required and count == 0:
                indicators_without_profiles.append(indicator_id)
        elif profile_required:
            indicators_without_profiles.append(indicator_id)

        if map_path.exists():
            map_files += 1
            map_payload = _read_json(map_path)
            values = map_payload.get("values", [])
            map_values += sum(value.get("value") is not None for value in values)
            map_suppressed += sum(bool(value.get("suppressed")) for value in values)
            map_status = str(map_payload.get("status", indicator.get("mapStatus", "unknown")))
            map_status_counts[map_status] = map_status_counts.get(map_status, 0) + 1
            if not values:
                indicators_without_maps.append(indicator_id)
        else:
            indicators_without_maps.append(indicator_id)

    gate = release.get("publicationGate", {})
    pending_gates = sorted(key for key, value in gate.items() if value in {"pending", "blocked"})
    missing_denominators = release.get("coverage", {}).get("missingDenominatorYears", [])

    download_path = output_root / "downloads" / "series-publicas.csv"
    if download_path.exists():
        with download_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("suppressed", "").lower() == "true":
                    leaked_fields = [
                        field for field in ("value", "count", "ciLow", "ciHigh")
                        if row.get(field, "") not in {"", "null", "None"}
                    ]
                    if leaked_fields:
                        download_suppression_leaks.append(
                            {"outcomeId": row.get("outcomeId"), "period": row.get("period"), "fields": leaked_fields}
                        )

    if release.get("status") != "public_release_ready":
        findings.append(
            _finding(
                "release-not-public",
                "blocker",
                "A release ainda está marcada como beta técnica",
                f"status={release.get('status', 'ausente')}",
                "Concluir as revisões e mudar o status somente após aprovação formal.",
            )
        )
    if pending_gates:
        findings.append(
            _finding(
                "review-gates-pending",
                "blocker",
                "Há portões de revisão pendentes",
                ", ".join(pending_gates),
                "Registrar revisão epidemiológica, acessibilidade e proveniência no manifesto.",
            )
        )
    if indicators_without_maps:
        findings.append(
            _finding(
                "municipal-map-not-publishable",
                "blocker",
                "O mapa municipal ainda não tem valores de saúde publicados",
                f"{len(indicators_without_maps)}/{len(indicators)} indicadores estão com malha contextual e values vazio.",
                "Validar taxas por residência municipal ou manter o mapa explicitamente fora da release pública.",
            )
        )
    if sih_indicators and sih_with_brazil != sih_indicators:
        findings.append(
            _finding(
                "sih-brazil-comparator-missing",
                "blocker",
                "O comparador Brasil está ausente para o SIH",
                f"{sih_with_brazil}/{sih_indicators} indicadores SIH têm brazil_total.",
                "Adquirir e reconciliar a tabulação nacional equivalente por residência antes de anunciar a comparação Brasil.",
            )
        )
    if indicators_without_profiles:
        findings.append(
            _finding(
                "profiles-incomplete",
                "blocker",
                "Os perfis idade/sexo estão incompletos",
                f"{len(indicators_without_profiles)}/{len(profile_eligible_indicators)} indicadores SIM elegíveis não têm observações de perfil.",
                "Publicar somente perfis SIM validados ou retirar o módulo de perfis da promessa de lançamento.",
            )
        )
    if missing_denominators:
        findings.append(
            _finding(
                "denominator-gaps",
                "warning",
                "Existem anos sem denominador oficial",
                ", ".join(str(year) for year in missing_denominators),
                "Manter esses anos como lacunas; para 2023, monitorar eventual publicação oficial compatível e regenerar as séries somente após validação, sem interpolar.",
            )
        )
    if schema_missing:
        findings.append(
            _finding(
                "contract-incomplete",
                "blocker",
                "Há artefatos fora do contrato JSON",
                f"{len(schema_missing)} observações ou arquivos com campos ausentes.",
                "Corrigir o pipeline antes da publicação.",
            )
        )
    if unsuppressed_small_cells:
        findings.append(
            _finding(
                "small-cell-leak",
                "blocker",
                "Há células pequenas sem supressão",
                f"{len(unsuppressed_small_cells)} observações têm contagem menor que 5.",
                "Interromper a release e aplicar supressão no pipeline.",
            )
        )
    if download_suppression_leaks:
        findings.append(
            _finding(
                "download-suppression-leak",
                "blocker",
                "O download público expõe campos de células suprimidas",
                f"{len(download_suppression_leaks)} linhas mantêm valor, contagem ou intervalo após supressão.",
                "Interromper a release e remover os campos antes de disponibilizar o CSV.",
            )
        )
    if profile_suppression_leaks:
        findings.append(
            _finding(
                "profile-suppression-leak", "blocker",
                "Um perfil público expõe uma célula protegida",
                f"{len(profile_suppression_leaks)} células mantêm numerador, taxa ou intervalo.",
                "Remover os campos derivados antes de gerar os JSON públicos.",
            )
        )
    sim_profile_indicators = [
        item for item in indicators
        if item.get("source") == "SIM" and item.get("profileCoverage", {}).get("status") == "available"
    ]
    if sim_profile_indicators and len(profile_municipality_codes) != 92:
        findings.append(
            _finding(
                "profile-municipality-coverage", "blocker",
                "A cobertura municipal dos perfis não contém 92 códigos",
                f"Foram encontrados {len(profile_municipality_codes)} códigos municipais nos perfis SIM.",
                "Reconciliar a matriz municipal e regenerar os contratos públicos.",
            )
        )

    non_verified_sources = []
    source_catalog = root / "metadata" / "source_catalog.csv"
    if source_catalog.exists():
        with source_catalog.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("status") not in {"verified", ""}:
                    non_verified_sources.append(
                        {"sourceId": row.get("source_id"), "status": row.get("status")}
                    )
    if non_verified_sources:
        findings.append(
            _finding(
                "source-catalog-open-items",
                "warning",
                "O catálogo de fontes ainda tem itens fora de verified",
                ", ".join(f"{item['sourceId']}={item['status']}" for item in non_verified_sources),
                "Resolver ou marcar claramente como fonte futura fora do escopo da release.",
            )
        )

    if status_counts.get("provisional", 0):
        findings.append(
            _finding(
                "provisional-observations",
                "warning",
                "A série contém observações provisórias",
                f"{status_counts['provisional']} observações com dataStatus=provisional.",
                "Manter o rótulo provisório e indicar a data de atualização da fonte.",
            )
        )

    blocker_count = sum(item["severity"] == "blocker" for item in findings)
    warning_count = sum(item["severity"] == "warning" for item in findings)
    readiness_status = "blocked_for_public_release" if blocker_count else "public_release_ready"
    return {
        "schemaVersion": "1.0.0",
        "checkedAt": _utc_now(),
        "releaseId": release.get("releaseId"),
        "status": readiness_status,
        "publicationAllowed": blocker_count == 0,
        "summary": {
            "blockerCount": blocker_count,
            "warningCount": warning_count,
            "indicatorCount": len(indicators),
            "seriesFiles": series_files,
            "profileFiles": profile_files,
            "mapFiles": map_files,
            "observations": observations,
            "suppressedObservations": suppressed,
            "profileObservations": profile_observations,
            "profileEligibleIndicators": len(profile_eligible_indicators),
            "mapValues": map_values,
            "mapSuppressedValues": map_suppressed,
            "sihIndicators": sih_indicators,
            "sihWithBrazilComparator": sih_with_brazil,
            "missingDenominatorYears": missing_denominators,
            "downloadSuppressionLeaks": len(download_suppression_leaks),
            "profileSuppressionLeaks": len(profile_suppression_leaks),
            "profileMunicipalityCount": len(profile_municipality_codes),
        },
        "checks": {
            "requiredObservationFields": sorted(REQUIRED_OBSERVATION_FIELDS),
            "schemaMissing": schema_missing,
            "unsuppressedSmallCells": unsuppressed_small_cells,
            "downloadSuppressionLeaks": download_suppression_leaks,
            "profileSuppressionLeaks": profile_suppression_leaks,
            "mapStatusCounts": map_status_counts,
            "sourceCounts": source_counts,
            "dataStatusCounts": status_counts,
            "pendingPublicationGates": pending_gates,
            "nonVerifiedSources": non_verified_sources,
        },
        "indicatorsWithoutProfiles": indicators_without_profiles,
        "profileEligibleIndicators": profile_eligible_indicators,
        "indicatorsWithoutMaps": indicators_without_maps,
        "findings": findings,
        "nextActions": [item["action"] for item in findings],
    }


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Pré-voo de lançamento do Portal Observatório Saúde & Ambiente",
        "",
        f"Verificação: `{report['checkedAt']}`",
        f"Release: `{report.get('releaseId')}`",
        f"Status: **{report['status']}**",
        "",
        "## Resumo",
        "",
        f"- Bloqueios públicos: **{summary['blockerCount']}**",
        f"- Avisos: **{summary['warningCount']}**",
        f"- Indicadores: **{summary['indicatorCount']}**",
        f"- Observações públicas: **{summary['observations']}**",
        f"- Células suprimidas: **{summary['suppressedObservations']}**",
        f"- Indicadores SIM elegíveis para perfis: **{summary['profileEligibleIndicators']}**",
        f"- Observações de perfis idade/sexo: **{summary['profileObservations']}**",
        f"- Valores municipais no mapa: **{summary['mapValues']}**",
        f"- Células municipais suprimidas no mapa: **{summary.get('mapSuppressedValues', 0)}**",
        f"- Comparadores Brasil no SIH: **{summary['sihWithBrazilComparator']}/{summary['sihIndicators']}**",
        f"- Vazamentos de supressão no download: **{summary.get('downloadSuppressionLeaks', 0)}**",
        "",
        "## Achados",
        "",
    ]
    for item in report["findings"]:
        lines.extend(
            [
                f"### [{item['severity'].upper()}] {item['title']}",
                "",
                item["detail"],
                "",
                f"Ação: {item['action']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Escopo seguro da release",
            "",
            "- Séries agregadas por residência, sem dados pessoais.",
            "- SIH interpretado como eventos/AIHs; SIM interpretado como mortalidade, não incidência.",
            "- O módulo de perfis idade/sexo cobre o SIM em 2022; SIH não é apresentado como perfil neste lançamento.",
            "- Células com contagem menor que cinco não chegam ao frontend.",
            "- Anos sem denominador permanecem como lacunas, sem interpolação.",
            "- Nenhuma associação ecológica autoriza atribuir causalidade à CSN ou a outra fonte.",
            "",
            "## Critério de liberação",
            "",
            "A publicação pública só é permitida quando `publicationAllowed=true`, os portões de revisão estiverem aprovados e os textos do portal refletirem o escopo efetivamente coberto.",
            "",
        ]
    )
    return "\n".join(lines)


def write_portal_preflight(root: Path) -> tuple[Path, Path, dict[str, Any]]:
    report = assess_portal_release(root)
    quality_path = root / "reports" / "quality" / "portal_release_preflight.json"
    technical_path = root / "reports" / "technical" / "portal_lancamento.md"
    public_path = root / "site" / "public" / "data" / "launch-readiness.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    technical_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    quality_path.write_text(serialized, encoding="utf-8")
    technical_path.write_text(_markdown_report(report), encoding="utf-8")
    public_path.write_text(serialized, encoding="utf-8")

    release_path = root / "site" / "public" / "data" / "release.json"
    release = _read_json(release_path)
    release["readiness"] = {
        "status": report["status"],
        "publicationAllowed": report["publicationAllowed"],
        **report["summary"],
        "checkedAt": report["checkedAt"],
    }
    artifacts = [item for item in release.get("artifacts", []) if item.get("path") != "launch-readiness.json"]
    artifacts.append(
        {
            "path": "launch-readiness.json",
            "bytes": public_path.stat().st_size,
            "sha256": _sha256(public_path),
        }
    )
    release["artifacts"] = sorted(artifacts, key=lambda item: item["path"])
    release_path.write_text(json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return quality_path, technical_path, report
