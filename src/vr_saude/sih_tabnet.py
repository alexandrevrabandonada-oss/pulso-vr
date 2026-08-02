from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
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


def query_residence(root: Path, year: int, month: int, timeout: int = 60) -> SihQueryResult:
    definition = _get(SIH_RESIDENCE_DEF_URL, timeout).decode("latin1")
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


def save_query_response(root: Path, result: SihQueryResult) -> Path:
    destination = root / "data" / "raw" / f"sih_tabnet_nrrj_{result.year}_{result.month:02d}.html"
    destination.write_bytes(result.response)
    digest = sha256_file(destination)
    write_sha256_sidecar(destination, digest)
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
            "status": "downloaded",
            "records": result.hospitalizations,
            "sha256": digest,
            "raw_path": str(destination.relative_to(root)),
            "validation_summary": "TabNet POST por residência; resposta HTML preservada",
        },
    )
    return destination
