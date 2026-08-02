from __future__ import annotations

import json
import re
import urllib.request
from html import unescape
from pathlib import PurePosixPath
from typing import Any


DATASET_PAGES = {
    "sim": "https://dadosabertos.saude.gov.br/dataset/sim",
    "sivep": "https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026",
}


def discover_resources(dataset: str, timeout: int = 60) -> list[dict[str, Any]]:
    """Read the official portal's server-rendered resource catalog."""
    try:
        page_url = DATASET_PAGES[dataset]
    except KeyError as exc:
        raise ValueError(f"Unknown dataset {dataset!r}") from exc
    request = urllib.request.Request(page_url, headers={"User-Agent": "vr-saude-ambiental/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8")
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        raise RuntimeError(f"Official resource catalog was not found in {page_url}")
    payload = json.loads(unescape(match.group(1)))
    resources = payload.get("props", {}).get("pageProps", {}).get("resources", [])
    if not isinstance(resources, list):
        raise RuntimeError(f"Official resource catalog has an unexpected shape: {page_url}")
    return resources


def select_resource(
    resources: list[dict[str, Any]],
    year: int,
    preferred_formats: tuple[str, ...] = ("PARQUET", "CSV", "XML", "JSON"),
) -> dict[str, Any]:
    """Select one resource for a year, prioritizing analysis-friendly formats."""
    year_text = str(year)
    candidates = [
        resource
        for resource in resources
        if year_text in str(resource.get("name", "")) or year_text in str(resource.get("url", ""))
    ]
    for preferred in preferred_formats:
        for resource in candidates:
            declared = str(resource.get("format", "")).upper()
            url_suffix = PurePosixPath(str(resource.get("url", "")).split("?", 1)[0]).suffix.upper().lstrip(".")
            name_upper = str(resource.get("name", "")).upper()
            effective = declared or url_suffix
            if preferred.upper() in {effective, url_suffix, name_upper.split()[-1]}:
                selected = dict(resource)
                selected["format"] = effective
                return selected
    if candidates:
        selected = dict(candidates[0])
        if not selected.get("format"):
            selected["format"] = PurePosixPath(
                str(selected.get("url", "")).split("?", 1)[0]
            ).suffix.upper().lstrip(".")
        return selected
    raise LookupError(f"No resource found for year {year}")
