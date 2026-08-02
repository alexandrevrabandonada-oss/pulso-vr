from __future__ import annotations

from .download import SAMPLE_SOURCES


def get_sample_source(source_id: str) -> dict[str, str]:
    try:
        return SAMPLE_SOURCES[source_id]
    except KeyError as exc:
        available = ", ".join(sorted(SAMPLE_SOURCES))
        raise KeyError(f"Unknown source {source_id!r}. Available: {available}") from exc
