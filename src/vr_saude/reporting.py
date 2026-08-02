from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .provenance import sha256_file


def _markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def write_respiratory_report(root: Path) -> Path:
    inputs = sorted((root / "data" / "interim").glob("sih_morbidity_*.csv"))
    if not inputs:
        raise FileNotFoundError("no SIH morbidity interim CSV was found")
    frames = [pd.read_csv(path) for path in inputs]
    data = pd.concat(frames, ignore_index=True)
    key_columns = ["period", "geography", "outcome_id"]
    duplicate_rows = int(data.duplicated(key_columns).sum())
    data = data.sort_values(key_columns).drop_duplicates(key_columns, keep="last")
    data["value"] = pd.to_numeric(data["value"], errors="raise").astype(int)
    periods = sorted(data["period"].astype(str).unique())
    expected_periods = pd.period_range(periods[0], periods[-1], freq="M").astype(str).tolist()
    missing_periods = [period for period in expected_periods if period not in periods]
    negatives = int((data["value"] < 0).sum())
    summary = (
        data.groupby(["outcome_id", "outcome_label", "geography"], as_index=False)["value"]
        .sum()
        .sort_values(["outcome_id", "geography"])
    )
    table_rows = [
        [row.outcome_id, row.geography, int(row.value)]
        for row in summary.itertuples(index=False)
    ]
    source_rows = [
        [path.relative_to(root), sha256_file(path), len(pd.read_csv(path))]
        for path in inputs
    ]
    report = root / "reports" / "technical" / "fase3_respiratorio.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Fase 3 — primeira série respiratória do SIH",
                "",
                f"Execução: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
                "",
                "## Escopo",
                "",
                "Esta entrega tabula internações agregadas do SIH por município de residência, "
                "usando a Lista Morb CID-10 do TabNet. Volta Redonda é comparada ao total do "
                "RJ e ao restante do RJ calculado como total estadual menos VR.",
                "",
                "O produto é descritivo e estrutural. Não representa pessoas únicas, casos novos, "
                "taxas, incidência, mortalidade, excesso ou causalidade.",
                "",
                "## Cobertura e controle",
                "",
                f"- Competências observadas: **{periods[0]} a {periods[-1]}** ({len(periods)} meses).",
                f"- Competências ausentes dentro do intervalo: **{len(missing_periods)}** "
                f"({', '.join(missing_periods) if missing_periods else 'nenhuma'}).",
                f"- Linhas duplicadas removidas ao combinar janelas: **{duplicate_rows}**.",
                f"- Valores negativos: **{negatives}**.",
                "- O símbolo `-` da legenda oficial do TabNet foi convertido para zero numérico, "
                "pois a própria legenda o define como zero não resultante de arredondamento.",
                "",
                "## Soma dos eventos agregados por janela completa",
                "",
                _markdown_table(["desfecho", "território", "internações agregadas"], table_rows),
                "",
                "## Arquivos intermediários usados",
                "",
                _markdown_table(["arquivo", "SHA-256", "linhas lidas"], source_rows),
                "",
                "## Limites para a análise seguinte",
                "",
                "- A Lista Morb é uma agregação oficial do TabNet; o dicionário CID e a "
                "reconciliação com totais independentes ainda devem ser fechados.",
                "- O denominador populacional agregado já pode ser integrado; idade/sexo, taxas "
                "específicas e intervalos de confiança ainda não são liberados.",
                "- SIH é uma contagem de internações/AIH e não deve ser interpretado como "
                "número de indivíduos.",
                "- 2025–2026-05 permanece provisório conforme a atualização do TabNet.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report
