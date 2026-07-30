"""Tests for normalized filename identity matching."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import GDI_PROFILE, HSAB_PROFILE, OutputType
from output_verifier.file_matcher import match_files_for_output
from output_verifier.models import DiscoveredOutput, ScenarioKey
from output_verifier.utilities.filename_utils import (
    build_normalized_identity_from_rule,
    normalize_filename_identity,
)


def _scenario(output_type: OutputType = OutputType.LH1) -> ScenarioKey:
    return ScenarioKey(scenario_path="s1", run_type="current", output_type=output_type)


def _discovered(
    expected_files: list[Path],
    actual_files: list[Path],
    output_type: OutputType = OutputType.LH1,
) -> DiscoveredOutput:
    return DiscoveredOutput(
        scenario_key=_scenario(output_type),
        expected_folder=Path("expected"),
        actual_folder=Path("actual"),
        expected_files=tuple(expected_files),
        actual_files=tuple(actual_files),
    )


def test_datetime_differs_but_pattern_matches(tmp_path: Path) -> None:
    expected = tmp_path / "GDI_LH1_20260730110000.xml"
    actual = tmp_path / "GDI_LH1_20260730120000.xml"
    expected.write_text("<a/>", encoding="utf-8")
    actual.write_text("<a/>", encoding="utf-8")

    pairs = match_files_for_output(_discovered([expected], [actual]), GDI_PROFILE)

    assert len(pairs) == 1
    assert pairs[0].normalized_identity == "GDI_LH1_<datetime>.xml"
    assert pairs[0].is_valid_pattern


def test_hb1_does_not_match_hb2(tmp_path: Path) -> None:
    hb1 = tmp_path / "HB1_HSAB_CLAIMS_20260730110000.xml"
    hb2 = tmp_path / "HB2_HSAB_CLAIMS_20260730110000.xml"
    hb1.write_text("<a/>", encoding="utf-8")
    hb2.write_text("<a/>", encoding="utf-8")

    pairs = match_files_for_output(
        _discovered([hb1], [hb2], OutputType.WEX),
        HSAB_PROFILE,
    )

    assert len(pairs) == 2
    identities = {pair.normalized_identity for pair in pairs}
    assert identities == {
        "HB1_HSAB_CLAIMS_<datetime>.xml",
        "HB2_HSAB_CLAIMS_<datetime>.xml",
    }


def test_manual_does_not_match_patient_manual(tmp_path: Path) -> None:
    manual = tmp_path / "GDI_MANUAL_20260730110000.csv"
    patient = tmp_path / "GDI_MANUAL_PATIENT_20260730110000.csv"
    manual.write_text("a\n", encoding="utf-8")
    patient.write_text("a\n", encoding="utf-8")

    pairs = match_files_for_output(
        _discovered([manual], [patient], OutputType.MANUAL),
        GDI_PROFILE,
    )
    assert len(pairs) == 2


def test_multiple_files_same_pattern_sorted(tmp_path: Path) -> None:
    expected_b = tmp_path / "GDI_LH1_20260730110002.xml"
    expected_a = tmp_path / "GDI_LH1_20260730110001.xml"
    actual_a = tmp_path / "GDI_LH1_20260730120001.xml"
    actual_b = tmp_path / "GDI_LH1_20260730120002.xml"
    for path in (expected_a, expected_b, actual_a, actual_b):
        path.write_text("<a/>", encoding="utf-8")

    pairs = match_files_for_output(
        _discovered([expected_b, expected_a], [actual_b, actual_a]),
        GDI_PROFILE,
    )
    assert len(pairs) == 2
    assert pairs[0].expected_file.name.endswith("10001.xml")
    assert pairs[0].actual_file.name.endswith("20001.xml")
    assert pairs[1].expected_file.name.endswith("10002.xml")


def test_expected_count_greater_than_actual(tmp_path: Path) -> None:
    e1 = tmp_path / "GDI_LH1_20260730110001.xml"
    e2 = tmp_path / "GDI_LH1_20260730110002.xml"
    a1 = tmp_path / "GDI_LH1_20260730120001.xml"
    for path in (e1, e2, a1):
        path.write_text("<a/>", encoding="utf-8")

    pairs = match_files_for_output(_discovered([e1, e2], [a1]), GDI_PROFILE)
    assert len(pairs) == 2
    assert pairs[1].actual_file is None


def test_actual_count_greater_than_expected(tmp_path: Path) -> None:
    e1 = tmp_path / "GDI_LH1_20260730110001.xml"
    a1 = tmp_path / "GDI_LH1_20260730120001.xml"
    a2 = tmp_path / "GDI_LH1_20260730120002.xml"
    for path in (e1, a1, a2):
        path.write_text("<a/>", encoding="utf-8")

    pairs = match_files_for_output(_discovered([e1], [a1, a2]), GDI_PROFILE)
    assert len(pairs) == 2
    assert pairs[1].expected_file is None


def test_invalid_filename_pattern(tmp_path: Path) -> None:
    bad = tmp_path / "GDI_LH1_BAD.xml"
    bad.write_text("<a/>", encoding="utf-8")
    pairs = match_files_for_output(_discovered([bad], [bad]), GDI_PROFILE)
    assert len(pairs) == 1
    assert pairs[0].is_valid_pattern is False
    assert pairs[0].file_format is None


def test_normalize_filename_identity() -> None:
    assert (
        normalize_filename_identity("LumeLight.ClaimFeed.20260730110000.mbi")
        == "LumeLight.ClaimFeed.<datetime>.mbi"
    )
