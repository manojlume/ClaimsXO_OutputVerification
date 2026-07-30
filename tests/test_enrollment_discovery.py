"""EnrollmentXO discovery and filename identity tests."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import (
    ENROLLMENT_XO_ABG_PROFILE,
    ENROLLMENT_XO_GDI_PROFILE,
    ENROLLMENT_XO_HSAB_PROFILE,
    OutputType,
    SolutionType,
    VerificationType,
)
from output_verifier.file_matcher import match_files_for_output
from output_verifier.folder_discovery import discover_output_locations
from output_verifier.models import DiscoveredOutput, ScenarioKey
from output_verifier.utilities.filename_utils import build_normalized_identity_from_rule


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_abg_discovers_alegeus_and_reports(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(root / "s1" / "current" / "alegeus" / "Export_20260730141107524_Cafeteria_XML_20210301_0002.mbi")
    _touch(root / "s1" / "current" / "reports" / "ExceptionReport_20260730141402865_Cafeteria_XML_20210301_0036.csv")
    discovered = discover_output_locations(root, SolutionType.ENROLLMENT_XO, VerificationType.ABG)
    outputs = {key.output_type for key in discovered}
    assert outputs == {OutputType.ALEGEUS, OutputType.REPORTS}


def test_gdi_discovers_wexhealth_and_reports(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(root / "s1" / "pre" / "WexHealth" / "GDI_WEXHealth_20240710125335036.txt")
    _touch(
        root / "s1" / "pre" / "reports" / "GDI_ChangeReport_GDI_EN_ALL_12122022_after_20240710125331939.csv"
    )
    discovered = discover_output_locations(root, SolutionType.ENROLLMENT_XO, VerificationType.GDI)
    outputs = {key.output_type for key in discovered}
    assert outputs == {OutputType.WEX_HEALTH, OutputType.REPORTS}


def test_hsab_discovers_import_and_reports(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(
        root
        / "nested"
        / "s1"
        / "current"
        / "HSABEnrollmentImport"
        / "202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_20260728230014069.txt"
    )
    _touch(
        root
        / "nested"
        / "s1"
        / "current"
        / "reports"
        / "HSAB_ChangeReport_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_20260728230012020.csv"
    )
    discovered = discover_output_locations(root, SolutionType.ENROLLMENT_XO, VerificationType.HSAB)
    key = next(iter(discovered))
    assert "nested\\s1" in key.scenario_path or key.scenario_path.endswith("s1")
    assert {item.output_type for item in discovered} == {
        OutputType.HSAB_ENROLLMENT_IMPORT,
        OutputType.REPORTS,
    }


def test_case_insensitive_enrollment_output_folder(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _touch(root / "s1" / "CURRENT" / "ALEGEUS" / "Export_20260730141107524_Cafeteria_XML_20210301_0002.mbi")
    discovered = discover_output_locations(root, SolutionType.ENROLLMENT_XO, VerificationType.ABG)
    key = next(iter(discovered))
    assert key.run_type == "current"
    assert key.output_type == OutputType.ALEGEUS


def test_abg_export_runtime_ignored() -> None:
    rule = ENROLLMENT_XO_ABG_PROFILE.output_folders[0].filename_rules[0]
    identity = build_normalized_identity_from_rule(
        rule,
        "Export_20260730141107524_Cafeteria_XML_20210301_0002.mbi",
    )
    assert identity == "Export_<runtime_timestamp>_Cafeteria_XML_20210301_0002.mbi"


def test_gdi_change_report_final_runtime_ignored() -> None:
    rule = ENROLLMENT_XO_GDI_PROFILE.output_folders[1].filename_rules[0]
    identity = build_normalized_identity_from_rule(
        rule,
        "GDI_ChangeReport_GDI_EN_ALL_12122022_after_20240710125331939.csv",
    )
    assert identity == "GDI_ChangeReport_GDI_EN_ALL_12122022_after_<runtime_timestamp>.csv"


def test_hsab_import_final_runtime_ignored() -> None:
    rule = ENROLLMENT_XO_HSAB_PROFILE.output_folders[0].filename_rules[0]
    identity = build_normalized_identity_from_rule(
        rule,
        "202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_20260728230014069.txt",
    )
    assert (
        identity
        == "202162_PROD_WUT584_CollectiveHealth_394332_HSAB_Eligibility_20240101_061701_<runtime_timestamp>.txt"
    )


def test_abg_different_identities_do_not_match(tmp_path: Path) -> None:
    expected = tmp_path / "Export_111_Cafeteria_XML_20210301_0002.mbi"
    actual = tmp_path / "Export_222_Cafeteria_XML_20210301_0003.mbi"
    expected.write_text("a,b\n", encoding="utf-8")
    actual.write_text("a,b\n", encoding="utf-8")
    discovered = DiscoveredOutput(
        scenario_key=ScenarioKey("s1", "current", OutputType.ALEGEUS),
        expected_folder=tmp_path,
        actual_folder=tmp_path,
        expected_files=(expected,),
        actual_files=(actual,),
    )
    pairs = match_files_for_output(discovered, ENROLLMENT_XO_ABG_PROFILE)
    assert len(pairs) == 2
