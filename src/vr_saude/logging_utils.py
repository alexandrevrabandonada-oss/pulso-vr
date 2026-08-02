from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(root: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure a console and persistent file logger for one run."""
    log_path = root / "outputs" / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("vr_saude")
    logger.setLevel(level)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger
