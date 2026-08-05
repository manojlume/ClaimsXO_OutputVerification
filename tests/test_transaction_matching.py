"""Filename matching tests for TransactionXO–HSAB."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import OutputType, TRANSACTION_XO_HSAB_PROFILE
from output_verifier.file_matcher import match_files_for_output
from output_verifier.models import DiscoveredOutput, ScenarioKey


def _scenario(output_type: OutputType) -> ScenarioKey:
    return ScenarioKey(scenario_path="s1", run_type="current", output_type=output_type)


def _discovered(
    expected_files: list[Path],
    actual_files: list[Path],
    output_type: OutputType,
) -> DiscoveredOutput:
    return DiscoveredOutput(
        scenario_key=_scenario(output_type),
        expected_folder=Path("expected"),
        actual_folder=Path("actual"),
        expected_files=tuple(expected_files),
        actual_files=tuple(actual_files),
    )


def test_mdc_dynamic_values_match(tmp_path: Path) -> None:
    expected = tmp_path / "HSB_EN_2026062401_Converted.txt"
    actual = tmp_path / "HSB_EN_2026062499_Converted.txt"
    expected.write_text("A", encoding="utf-8")
    actual.write_text("A", encoding="utf-8")
    pairs = match_files_for_output(
        _discovered([expected], [actual], OutputType.MDC),
        TRANSACTION_XO_HSAB_PROFILE,
    )
    assert len(pairs) == 1
    assert pairs[0].normalized_identity == "HSB_EN_*_Converted.txt"
    assert pairs[0].is_valid_pattern


def test_dup_acct_never_matches_utp(tmp_path: Path) -> None:
    dup = tmp_path / "HSB_EN_2026062403_AllExceptions_ExceptionDupAcct_20260805104855.csv"
    utp = tmp_path / "HSB_EN_2026062403_AllExceptions_ExceptionUTP_20260805104855.csv"
    dup.write_text("a\n", encoding="utf-8")
    utp.write_text("a\n", encoding="utf-8")
    pairs = match_files_for_output(
        _discovered([dup], [utp], OutputType.MDC_EXCEPTIONS),
        TRANSACTION_XO_HSAB_PROFILE,
    )
    assert len(pairs) == 2
    identities = {pair.normalized_identity for pair in pairs}
    assert identities == {
        "HSB_EN_*_ExceptionDupAcct*.csv",
        "HSB_EN_*_ExceptionUTP_*.csv",
    }


def test_converted_never_matches_csv(tmp_path: Path) -> None:
    txt = tmp_path / "HSB_EN_1_Converted.txt"
    csv = tmp_path / "HSB_EN_1_All_ExceptionDupAcct_1.csv"
    txt.write_text("A", encoding="utf-8")
    csv.write_text("a\n", encoding="utf-8")
    pairs = match_files_for_output(
        _discovered([txt], [csv], OutputType.MDC),
        TRANSACTION_XO_HSAB_PROFILE,
    )
    assert len(pairs) == 2


def test_invalid_filename_pattern(tmp_path: Path) -> None:
    bad = tmp_path / "HSB_EN_Converted.txt"
    bad.write_text("A", encoding="utf-8")
    pairs = match_files_for_output(
        _discovered([bad], [bad], OutputType.MDC),
        TRANSACTION_XO_HSAB_PROFILE,
    )
    assert len(pairs) == 1
    assert pairs[0].is_valid_pattern is False


def test_multiple_same_identity_sorted(tmp_path: Path) -> None:
    e1 = tmp_path / "HSB_EN_A_Converted.txt"
    e2 = tmp_path / "HSB_EN_B_Converted.txt"
    a1 = tmp_path / "HSB_EN_C_Converted.txt"
    a2 = tmp_path / "HSB_EN_D_Converted.txt"
    for path in (e1, e2, a1, a2):
        path.write_text("A", encoding="utf-8")
    pairs = match_files_for_output(
        _discovered([e2, e1], [a2, a1], OutputType.MDC),
        TRANSACTION_XO_HSAB_PROFILE,
    )
    assert len(pairs) == 2
    assert pairs[0].expected_file.name == "HSB_EN_A_Converted.txt"
    assert pairs[0].actual_file.name == "HSB_EN_C_Converted.txt"
    assert pairs[1].expected_file.name == "HSB_EN_B_Converted.txt"
