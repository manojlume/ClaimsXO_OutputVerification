"""Tests for scenario and output folder discovery."""

from __future__ import annotations

from pathlib import Path

from output_verifier.constants import OutputType, VerificationType
from output_verifier.folder_discovery import build_scenario_inventory, discover_output_locations


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_single_level_scenario(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "test_58545" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")

    discovered = discover_output_locations(root, VerificationType.GDI)

    assert len(discovered) == 1
    key = next(iter(discovered))
    assert key.scenario_path == "test_58545"
    assert key.run_type == "current"
    assert key.output_type == OutputType.LH1


def test_multi_level_scenario(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "test_aggregation" / "3" / "pre" / "LH1" / "GDI_LH1_20260730110000.xml")

    discovered = discover_output_locations(root, VerificationType.GDI)
    key = next(iter(discovered))
    assert key.scenario_path == "test_aggregation\\3"
    assert key.run_type == "pre"
    assert key.output_type == OutputType.LH1


def test_all_supported_run_types(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    for index, run_type in enumerate(("current", "pre", "prepre", "hold")):
        _touch(
            root / "runs" / run_type / "LH1" / f"GDI_LH1_2026073011000{index}.xml",
            "<a/>",
        )

    discovered = discover_output_locations(root, VerificationType.GDI)
    assert {key.run_type for key in discovered} == {"current", "pre", "prepre", "hold"}


def test_unknown_folders_and_unsupported_files_ignored(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "s1" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")
    _touch(root / "s1" / "current" / "LH1" / "readme.txt")
    _touch(root / "s1" / "current" / "OTHER" / "file.xml")
    _touch(root / "s1" / "draft" / "LH1" / "GDI_LH1_20260730110001.xml")

    inventory = build_scenario_inventory(root, root, VerificationType.GDI)
    assert len(inventory) == 1
    assert len(inventory[0].expected_files) == 1
    assert inventory[0].expected_files[0].name.endswith(".xml")


def test_expected_only_and_actual_only(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    _touch(expected / "only_expected" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")
    _touch(actual / "only_actual" / "current" / "LH1" / "GDI_LH1_20260730110000.xml")

    inventory = build_scenario_inventory(expected, actual, VerificationType.GDI)
    assert len(inventory) == 2
    by_scenario = {item.scenario_key.scenario_path: item for item in inventory}
    assert by_scenario["only_expected"].actual_folder is None
    assert by_scenario["only_actual"].expected_folder is None


def test_empty_scenario(tmp_path: Path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    (expected / "empty" / "current" / "LH1").mkdir(parents=True)
    (actual / "empty" / "current" / "LH1").mkdir(parents=True)

    inventory = build_scenario_inventory(expected, actual, VerificationType.GDI)
    assert len(inventory) == 1
    assert inventory[0].expected_files == ()
    assert inventory[0].actual_files == ()


def test_case_insensitive_folder_recognition(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "s1" / "CURRENT" / "lh1" / "GDI_LH1_20260730110000.xml")

    discovered = discover_output_locations(root, VerificationType.GDI)
    key = next(iter(discovered))
    assert key.run_type == "current"
    assert key.output_type == OutputType.LH1


def test_hsab_wex_discovery(tmp_path: Path) -> None:
    root = tmp_path / "Scenarios"
    _touch(root / "s1" / "current" / "WEX" / "HB1_HSAB_CLAIMS_20260730110000.xml")

    discovered = discover_output_locations(root, VerificationType.HSAB)
    key = next(iter(discovered))
    assert key.output_type == OutputType.WEX
