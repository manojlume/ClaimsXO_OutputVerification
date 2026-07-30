# ClaimsXO Output Verifier — Function Guide

**Package:** `output_verifier`  
**Purpose:** Module-by-module reference of public classes and functions in the current codebase.

Use this with [Developer_Guide.md](Developer_Guide.md) for business context.

---

## Table of contents

1. [Package entry](#1-package-entry)
2. [cli.py](#2-clipy)
3. [__main__.py](#3-__main__py)
4. [constants.py](#4-constantspy)
5. [models.py](#5-modelspy)
6. [config.py](#6-configpy)
7. [config_loader.py](#7-config_loaderpy)
8. [logging_setup.py](#8-logging_setuppy)
9. [folder_discovery.py](#9-folder_discoverypy)
10. [file_matcher.py](#10-file_matcherpy)
11. [verification_service.py](#11-verification_servicepy)
12. [comparators](#12-comparators)
13. [reporting/excel_reporter.py](#13-reportingexcel_reporterpy)
14. [utilities](#14-utilities)
15. [Quick call graph](#15-quick-call-graph)

---

## 1. Package entry

### `output_verifier/__init__.py`

| Symbol | Type | Description |
| --- | --- | --- |
| `__version__` | `str` | Package version string (`"1.0.0"`) |

### `output_verifier/__main__.py`

Enables `python -m output_verifier`.

---

## 2. `cli.py`

Command-line argument parsing and default config path resolution.

| Function | Signature | Description |
| --- | --- | --- |
| `application_directory` | `() -> Path` | Directory containing the running app. Frozen exe → folder of `sys.executable`. Source run → `Path.cwd()`. |
| `default_config_path` | `() -> Path` | Returns `{application_directory()}/config.yaml`. |
| `build_argument_parser` | `() -> argparse.ArgumentParser` | Builds parser with `--config`, `--verification-type`, `--expected-parent-folder`, `--actual-parent-folder`, `--report-output-folder`, `--log-level`. |
| `parse_arguments` | `(argv: list[str] \| None = None) -> Namespace` | Parses CLI args (uses `sys.argv` when `argv` is None). |
| `config_path_from_args` | `(arguments: Namespace) -> Path` | Returns `Path(arguments.config)`. |

**Constant:** `DEFAULT_CONFIG_FILE_NAME = "config.yaml"`

---

## 3. `__main__.py`

Process orchestration for one verification run.

| Function | Description |
| --- | --- |
| `print_console_summary(summary: ExecutionSummary) -> None` | Prints verification type, compared files, passed/failed/not verified, report path, exit code. |
| `print_system_error(message: str, exit_code: int = 2) -> None` | Prints concise stderr error + exit code for system failures. |
| `run(argv: list[str] \| None = None) -> int` | Full application flow; returns process exit code. |
| `main() -> None` | Calls `sys.exit(run())`. |

### `run()` internal sequence

1. `parse_arguments`  
2. `load_resolved_config`  
3. `immediate_parent_folder_name(actual_parent_folder)`  
4. `setup_logging(...)`  
5. `VerificationService(...).run()`  
6. `ExcelReporter().write_report(...)`  
7. `print_console_summary`  
8. Return exit code  

Catches `ConfigurationError`, `ValueError`, `OSError`, and unexpected exceptions → exit `2`.

---

## 4. `constants.py`

Application constants, enums, filename patterns, and TPA profile registry.

### 4.1 Scalar constants

| Name | Value / meaning |
| --- | --- |
| `APPLICATION_NAME` | `"output-verifier"` |
| `APPLICATION_VERSION` | `"1.0.0"` |
| `SOLUTION_TYPE` | `"ClaimsXO"` |
| `DATETIME_TOKEN` | `"<datetime>"` |
| `DATETIME_DIGIT_COUNT` | `14` |
| `DATETIME_PLACEHOLDER_PATTERN` | regex `\d{14}` |
| `MAX_REPORTED_DIFFERENCES` | `2` |
| `MAX_LOGGED_VALUE_LENGTH` | `200` |
| `MBI_DELIMITER` | `"\|"` |
| `SUPPORTED_RUN_FOLDERS` | `current`, `pre`, `prepre`, `hold` |
| `SUPPORTED_EXTENSIONS` | `.xml`, `.csv`, `.mbi` |
| `OUTPUT_TYPE_CANONICAL` | lower-case folder name → `OutputType` |
| `VALID_LOG_LEVELS` | standard logging level names |
| `HEX_COLOR_PATTERN` | `#RRGGBB` validator |

### 4.2 Enums

| Enum | Members |
| --- | --- |
| `VerificationType` | `GDI`, `HSAB` |
| `OutputType` | `LH1`, `MANUAL` (`manual`), `ALG`, `WEX` |
| `RunType` | `CURRENT`, `PRE`, `PREPRE`, `HOLD` |
| `VerificationStatus` | `PASSED`, `FAILED`, `NOT_VERIFIED` |
| `FileFormat` | `XML`, `CSV`, `MBI` |
| `ExitCode` | `SUCCESS=0`, `COMPARISON_FAILURE=1`, `SYSTEM_ERROR=2` |
| `DifferenceType` | Element/attribute/text/child-count mismatch categories |

### 4.3 Profile dataclasses

#### `FilenameRule` (frozen)

| Field | Meaning |
| --- | --- |
| `pattern` | Compiled regex with 14-digit datetime capture |
| `normalized_template` | Identity string using `<datetime>` |
| `file_format` | `FileFormat` |
| `ignore_rule_key` | Key into ignore-rule config (`lh1_xml_paths`, `manual_csv_columns`, …) |

#### `OutputFolderProfile` (frozen)

| Field | Meaning |
| --- | --- |
| `output_type` | `OutputType` |
| `filename_rules` | Tuple of `FilenameRule` |

#### `TpaProfile` (frozen)

| Method / field | Description |
| --- | --- |
| `verification_type` | TPA |
| `output_folders` | Supported output folder profiles |
| `supported_output_folder_names()` | Lower-case set of output folder names |
| `find_filename_rule(output_type, filename)` | First matching rule or `None` |

### 4.4 Registry

| Symbol | Description |
| --- | --- |
| `GDI_PROFILE` | GDI LH1/manual/ALG rules |
| `HSAB_PROFILE` | HSAB WEX HB1/HB2 rules |
| `TPA_PROFILES` | `dict[VerificationType, TpaProfile]` |
| `get_tpa_profile(verification_type)` | Lookup helper; raises `ValueError` if unsupported |

### 4.5 Filename pattern constants

| Constant | Matches |
| --- | --- |
| `GDI_LH1_PATTERNS` | Five LH1 XML variants |
| `GDI_MANUAL_PATTERN` | `GDI_MANUAL_<dt>.csv` |
| `GDI_MANUAL_PATIENT_PATTERN` | `GDI_MANUAL_PATIENT_<dt>.csv` |
| `GDI_MBI_PATTERN` | `LumeLight.ClaimFeed.<dt>.mbi` |
| `HSAB_HB1_PATTERN` / `HSAB_HB2_PATTERN` | WEX XML claims files |

---

## 5. `models.py`

### Config models

| Class | Description |
| --- | --- |
| `ReportConfig` | Report folder, base name, timestamp format, status colors |
| `LoggingConfig` | Level, console/file flags, folder, rotation settings |
| `IgnoreRulesConfig` | GDI/HSAB ignore lists + helper getters |
| `ResolvedConfig` | Complete resolved configuration for one run |

#### `IgnoreRulesConfig` helpers

| Method | Returns |
| --- | --- |
| `xml_paths_for(verification_type, ignore_rule_key)` | XML XPath ignore tuple |
| `csv_columns_for(ignore_rule_key)` | CSV header names to ignore |
| `mbi_field_positions()` | One-based MBI positions to ignore |

### Discovery / matching models

| Class | Description |
| --- | --- |
| `ScenarioKey` | `(scenario_path, run_type, output_type)` |
| `ScenarioLocation` | Physical folder under Expected or Actual |
| `DiscoveredOutput` | Expected/Actual folders + direct file lists |
| `FileIdentity` | Normalized name + format + validity |
| `MatchedFilePair` | One expected/actual pairing |

### Comparison / reporting models

| Class | Description |
| --- | --- |
| `ComparisonOptions` | Ignore lists for a comparator call |
| `ComparisonDifference` | One difference description + optional type/values/location |
| `ComparisonResult` | `status`, `issue`, `differences` |
| `ReportRow` | One Excel detail row |
| `ExecutionSummary` | Run metadata + rows + counts |

#### `ExecutionSummary` properties

| Property | Meaning |
| --- | --- |
| `total_rows` | Number of report rows |
| `passed_count` / `failed_count` / `not_verified_count` | Status counters |
| `compared_files_count` | Rows with file names or NotVerified |

---

## 6. `config.py`

Validation helpers and `ConfigurationError`.

| Symbol | Description |
| --- | --- |
| `ConfigurationError` | Raised for invalid/missing configuration |
| `parse_verification_type(value)` | Parse `GDI`/`HSAB` (case-insensitive) |
| `validate_solution_type(value)` | Must equal `ClaimsXO` |
| `validate_hex_color(color_name, value)` | `#RRGGBB` check |
| `validate_log_level(value)` | Valid logging level name |
| `validate_positive_integer(field_name, value)` | `> 0` |
| `validate_non_negative_integer(field_name, value)` | `>= 0` |
| `validate_timestamp_format(value)` | Must work with `strftime` |
| `validate_string_list(field_name, value)` | List of strings → tuple |
| `validate_mbi_field_positions(value)` | Positive ints; skips non-positive with error |
| `validate_xpath_list(field_name, paths)` | Syntax-check via `lxml.etree.XPath` |
| `require_existing_directory(field_name, path)` | Exists + is directory |
| `ensure_creatable_directory(field_name, path)` | Create parents if needed |

---

## 7. `config_loader.py`

YAML loading and resolution into `ResolvedConfig`.

| Symbol | Description |
| --- | --- |
| `DEFAULT_REPORT` | Default report section dict |
| `DEFAULT_LOGGING` | Default logging section dict |
| `load_yaml_file(config_path)` | Load YAML mapping; raise `ConfigurationError` on problems |
| `build_resolved_config(yaml_data, **overrides)` | Merge defaults + YAML + CLI into `ResolvedConfig` |
| `load_resolved_config(config_path, **overrides)` | `load_yaml_file` + `build_resolved_config` |

### Private helper

| Function | Description |
| --- | --- |
| `_merge_section(defaults, overrides)` | Deep-ish merge for nested dict sections |

### Notable `build_resolved_config` parameters

- `verification_type_override`
- `expected_parent_folder_override`
- `actual_parent_folder_override`
- `report_output_folder_override`
- `log_level_override`
- `validate_parent_folders` (True at runtime; tests may disable)

---

## 8. `logging_setup.py`

| Function | Description |
| --- | --- |
| `build_log_filename(verification_type, immediate_parent, timestamp_token)` | Builds `VerificationLog_<type>_<parent>_<timestamp>.Log` |
| `setup_logging(config, *, verification_type, immediate_parent, timestamp_token)` | Clears root handlers; adds console and/or rotating file handler; returns log path or `None` |

Log file is written under `LoggingConfig.output_folder`.

---

## 9. `folder_discovery.py`

| Function | Description |
| --- | --- |
| `discover_output_locations(root, verification_type)` | Returns `dict[ScenarioKey, Path]` of supported output folders under one root |
| `build_scenario_inventory(expected_root, actual_root, verification_type)` | Union inventory as `list[DiscoveredOutput]` with file lists |

### Private helpers

| Function | Description |
| --- | --- |
| `_canonicalize_run_type(folder_name)` | Lower-case supported run type or `None` |
| `_canonicalize_output_type(folder_name, profile)` | Canonical `OutputType` or `None` |
| `_collect_direct_files(folder)` | Supported-extension files directly under folder |

---

## 10. `file_matcher.py`

| Function | Description |
| --- | --- |
| `classify_file(file_path, discovered, profile)` | Build `FileIdentity` (pattern match or invalid pattern) |
| `match_files_for_output(discovered, profile)` | Group by identity, sort, pair by position → `list[MatchedFilePair]` |

---

## 11. `verification_service.py`

### Class `VerificationService`

| Method | Description |
| --- | --- |
| `__init__(config: ResolvedConfig)` | Loads TPA profile and comparator instances |
| `run()` | Inventory → verify each → return `(list[ReportRow], ExitCode)` |

### Important private methods

| Method | Description |
| --- | --- |
| `_verify_discovered_output` | Scenario-level missing/unexpected/empty + file matching |
| `_rows_from_matched_pairs` | Count-mismatch row + per-pair rows |
| `_compare_pair` | Missing/unexpected/invalid/content compare for one pair |
| `_compare_content` | Dispatch to XML/CSV/MBI comparator |
| `_build_comparison_options` | Map ignore_rule_key → `ComparisonOptions` |
| `_build_issue_text` | Combine summary issue + Difference 1/2 text |
| `_scenario_row` / `_file_row` | Construct `ReportRow` |

---

## 12. Comparators

### 12.1 `comparators/base_comparator.py`

| Symbol | Description |
| --- | --- |
| `FileComparator` | `Protocol` with `compare(expected_path, actual_path, options) -> ComparisonResult` |

### 12.2 `comparators/xml_comparator.py`

#### Public

| Class / method | Description |
| --- | --- |
| `XmlComparator.compare(...)` | Parse both XML files, apply ignores, structural compare |

#### Private helpers (important)

| Function | Description |
| --- | --- |
| `_truncate` | Truncate long values for logging/messages |
| `_local_name` / `_qualified_name` | Tag name helpers |
| `_to_local_name_xpath` | Rewrite simple absolute XPath to namespace-tolerant form |
| `_xpath_matches` | Try original XPath, then rewritten form |
| `_apply_ignore_paths` | Remove ignored elements/attributes from a tree |
| `_element_text` | Meaningful text vs whitespace-only formatting |
| `_node_path` | Human-readable path for difference messages |
| `_compare_elements` | Recursive positional structural comparison |

### 12.3 `comparators/csv_comparator.py`

| Symbol | Description |
| --- | --- |
| `CsvComparator.compare(...)` | Compare CSV header + positional rows |
| `_read_csv_rows(path)` | Read all rows via `csv.reader` (utf-8-sig) |
| `_remove_ignored_columns(rows, ignored_columns, side)` | Drop configured header columns |

### 12.4 `comparators/mbi_comparator.py`

| Symbol | Description |
| --- | --- |
| `MbiComparator.compare(...)` | Compare pipe-delimited MBI records |
| `_read_mbi_records(path)` | Parse with `csv.reader(delimiter='\|')` preserving trailing empties |
| `_remove_ignored_fields(records, ignored_positions)` | Drop one-based field positions |

---

## 13. `reporting/excel_reporter.py`

| Symbol | Description |
| --- | --- |
| `DETAIL_HEADERS` | Column titles for detail sheet |
| `COLUMN_WIDTHS` | Sensible widths by column index |
| `build_report_filename(report_config, verification_type, immediate_parent, timestamp)` | Builds `VerificationReport_<type>_<parent>_<timestamp>.xlsx` |
| `ExcelReporter.write_report(report_config, summary, *, immediate_parent, timestamp)` | Creates workbook under `report.output_folder` and returns path |

### Private helpers

| Function | Description |
| --- | --- |
| `_worksheet_name` | `GDI Verification` / `HSAB Verification` |
| `_status_fill` | Background color from YAML status colors |
| `_write_detail_sheet` | Header + rows + freeze + autofilter + wrap Issue |
| `_write_summary_sheet` | Run metadata and counts |

---

## 14. Utilities

### 14.1 `utilities/filename_utils.py`

| Function | Description |
| --- | --- |
| `has_supported_extension(filename)` | `.xml` / `.csv` / `.mbi` check |
| `normalize_filename_identity(filename)` | Replace first 14-digit token with `<datetime>` |
| `build_normalized_identity_from_rule(rule)` | Return `rule.normalized_template` |
| `match_filename_rule(profile, output_type, filename)` | Profile lookup wrapper |
| `is_supported_filename(profile, output_type, filename)` | Boolean pattern match |
| `immediate_parent_folder_name(folder_path)` | `folder_path.name` (Actual run folder name) |
| `build_run_artifact_filename(prefix, verification_type, immediate_parent, timestamp, extension)` | Shared naming for report/log artifacts |

### 14.2 `utilities/path_utils.py`

| Function | Description |
| --- | --- |
| `ensure_directory(path)` | `mkdir(parents=True, exist_ok=True)` and return path |
| `is_readable_directory(path)` | True if path is a directory |
| `relative_posix(path, root)` | Relative path string for display (falls back to absolute) |

---

## 15. Quick call graph

```text
main()
 └─ run()
     ├─ parse_arguments()
     ├─ load_resolved_config()
     │    ├─ load_yaml_file()
     │    └─ build_resolved_config()
     │         └─ validators in config.py
     ├─ immediate_parent_folder_name()
     ├─ setup_logging() / build_log_filename()
     ├─ VerificationService.run()
     │    ├─ build_scenario_inventory()
     │    │    └─ discover_output_locations() × 2
     │    └─ for each DiscoveredOutput:
     │         ├─ match_files_for_output()
     │         │    └─ classify_file()
     │         └─ XmlComparator / CsvComparator / MbiComparator.compare()
     ├─ ExcelReporter.write_report()
     │    └─ build_report_filename()
     └─ print_console_summary()
```

---

## Appendix A — Status / issue strings produced by code

These exact strings are emitted by `VerificationService` and appear in Excel:

- `Unexpected scenario exists only in Actual Outputs`
- `Expected scenario missing in Actual Outputs`
- `No files available for verification`
- `File count mismatch. Expected: {n}, Actual: {m}`
- `Unexpected actual file`
- `Expected file missing`
- `Unsupported or invalid filename pattern`
- `XML content mismatch`
- `CSV content mismatch`
- `MBI content mismatch`
- Plus comparator-specific parsing errors (`XML parsing error: ...`, etc.)

---

## Appendix B — Where to change what

| If you need to change… | Edit… |
| --- | --- |
| Supported filename patterns | `constants.py` TPA profiles |
| Run folder names | `RunType` / `SUPPORTED_RUN_FOLDERS` |
| Discovery behavior | `folder_discovery.py` |
| Matching / pairing rules | `file_matcher.py` |
| Scenario/file status decisions | `verification_service.py` |
| XML compare / ignore behavior | `comparators/xml_comparator.py` |
| CSV compare | `comparators/csv_comparator.py` |
| MBI compare | `comparators/mbi_comparator.py` |
| Report columns / naming | `reporting/excel_reporter.py` |
| Log naming | `logging_setup.py` |
| YAML fields / validation | `config_loader.py` + `config.py` |
| CLI flags | `cli.py` |
| Ignore values for a run | `config.yaml` only |

---

*Generated from the current `output_verifier` source tree. Prefer the source as the final authority if docs and code diverge.*
