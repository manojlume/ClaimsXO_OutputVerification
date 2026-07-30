"""Logging initialization with console and rotating file handlers."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from output_verifier.constants import SolutionType, VerificationType
from output_verifier.models import LoggingConfig
from output_verifier.utilities.filename_utils import build_run_artifact_filename
from output_verifier.utilities.path_utils import ensure_directory


def build_log_filename(
    solution_type: SolutionType,
    verification_type: VerificationType,
    immediate_parent: str,
    timestamp_token: str,
) -> str:
    """Build the verification log filename for the current run."""
    return build_run_artifact_filename(
        prefix="VerificationLog",
        solution_type=solution_type.value,
        verification_type=verification_type.value,
        immediate_parent=immediate_parent,
        timestamp=timestamp_token,
        extension=".Log",
    )


def setup_logging(
    config: LoggingConfig,
    *,
    solution_type: SolutionType,
    verification_type: VerificationType,
    immediate_parent: str,
    timestamp_token: str,
) -> Path | None:
    """Configure root logging handlers and return the log file path when used."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, config.level, logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_file_path: Path | None = None

    if config.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.level, logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if config.log_to_file:
        ensure_directory(config.output_folder)
        log_file_path = config.output_folder / build_log_filename(
            solution_type,
            verification_type,
            immediate_parent,
            timestamp_token,
        )
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, config.level, logging.INFO))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("output_verifier").info(
        "Logging initialized. Level=%s console=%s file=%s",
        config.level,
        config.log_to_console,
        log_file_path,
    )
    return log_file_path
