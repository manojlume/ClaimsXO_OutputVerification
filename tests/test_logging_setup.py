"""Tests for log filename construction."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import VerificationType
from output_verifier.logging_setup import build_log_filename, setup_logging
from output_verifier.models import LoggingConfig


def test_build_log_filename() -> None:
    name = build_log_filename(
        VerificationType.GDI,
        "20260612_000022_fullrun",
        "20260730133505",
    )
    assert name == "VerificationLog_GDI_20260612_000022_fullrun_20260730133505.Log"


def test_setup_logging_writes_named_file(tmp_path: Path) -> None:
    config = LoggingConfig(
        level="INFO",
        log_to_console=False,
        log_to_file=True,
        output_folder=tmp_path,
        max_bytes=10485760,
        backup_count=5,
    )
    path = setup_logging(
        config,
        verification_type=VerificationType.HSAB,
        immediate_parent="20260730_085924_fullrun",
        timestamp_token="20260730140000",
    )
    assert path is not None
    assert path.name == "VerificationLog_HSAB_20260730_085924_fullrun_20260730140000.Log"
    assert path.exists()
