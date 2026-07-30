# ClaimsXO Output Verifier

Python utility that compares **Expected Output** files against **Actual Output** files after a ClaimsXO QA regression run, then writes an Excel verification report.

Package name: `output_verifier`  
Main command: `python -m output_verifier --config config.yaml`  
Executable name: `output-verifier.exe`

`--config` defaults to `config.yaml` next to the executable (or in the current folder for source runs).

## Purpose

After QA has already produced Expected and Actual output trees, this tool:

1. Discovers supported scenario / run / output folders
2. Matches expected and actual files by normalized filename identity (datetime ignored)
3. Compares XML, CSV, and MBI content with configured ignore rules
4. Writes an Excel report and prints a console summary
5. Returns an exit code suitable for automation

## Supported TPAs

| Verification type | Output folders | File types |
| --- | --- | --- |
| **GDI** | `LH1`, `manual`, `ALG` | XML, CSV, MBI |
| **HSAB** | `WEX` | XML (`HB1` / `HB2`) |

### Supported GDI files

- `LH1`: `GDI_LH1_<datetime>.xml`, `GDI_LH1_MMS_<datetime>.xml`, `GDI_LH1_FLORES_<datetime>.xml`, `GDI_LH1_HNE_<datetime>.xml`, `GDI_REGEN_LH1_<datetime>.xml`
- `manual`: `GDI_MANUAL_<datetime>.csv`, `GDI_MANUAL_PATIENT_<datetime>.csv`
- `ALG`: `LumeLight.ClaimFeed.<datetime>.mbi`

### Supported HSAB files

- `WEX`: `HB1_HSAB_CLAIMS_<datetime>.xml`, `HB2_HSAB_CLAIMS_<datetime>.xml`

Datetime is exactly 14 digits: `yyyyMMddHHmmss`.

## Folder structure

Expected and Actual parent folders contain scenario trees in this logical form:

```text
<scenario_path>\<run_type>\<output_type>\
```

Supported run folders (case-insensitive; reported lower-case):

- `current`
- `pre`
- `prepre`
- `hold`

Example:

```text
Scenarios\test_aggregation\3\pre\LH1
```

Report values:

- Scenario: `test_aggregation\3`
- Run Type: `pre`
- Output Type: `LH1`

Point `expected_parent_folder` / `actual_parent_folder` at the root that contains those scenario paths (often the `Scenarios` folder).

Discovery rules:

- Recursively scan for supported run folders
- Only inspect supported output folders directly under a run folder
- Only read files directly under those output folders
- Ignore unsupported extensions (supported: `.xml`, `.csv`, `.mbi`)

## YAML configuration

Template: `config.yaml`

Important settings:

- `solution_type`: must be `ClaimsXO`
- `verification_type`: `GDI` or `HSAB`
- `expected_parent_folder` / `actual_parent_folder`
- `report.*` report naming, folder, and status colors
- `logging.*` console/file logging with rotation
- `ignore_rules.GDI` / `ignore_rules.HSAB`

Stable application rules (filename patterns, run folders, extensions, comparators) stay in Python code, not YAML.

### Ignore-rule examples

```yaml
ignore_rules:
  GDI:
    lh1_xml_paths:
      - "/LH1StandardClaimsExchange/@CreatedDateTime"
    manual_csv_columns:
      - "GeneratedTimestamp"
    patient_manual_csv_columns: []
    mbi_field_positions:
      - 7
  HSAB:
    wex_xml_paths:
      - "/Claims/@CreatedDateTime"
```

Notes:

- XML ignore paths use XPath; invalid XPath is a configuration error (exit code 2)
- CSV ignore columns match header names exactly (case-sensitive)
- MBI ignore positions are one-based positive integers

## Command-line examples

Development run (from repository root):

```bat
set PYTHONPATH=src
python -m output_verifier --config config.yaml --verification-type GDI --expected-parent-folder "H:\ExpectedOutputs" --actual-parent-folder "H:\ActualOutputs"
```

Or use the helper script:

```bat
run-output-verifier.cmd --verification-type GDI --expected-parent-folder "H:\ExpectedOutputs" --actual-parent-folder "H:\ActualOutputs"
```

CLI overrides (override YAML):

- `--config`
- `--verification-type`
- `--expected-parent-folder`
- `--actual-parent-folder`
- `--report-output-folder`
- `--log-level`

Configuration precedence:

1. Command-line argument
2. YAML value
3. Application default

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No Failed records (Passed and NotVerified allowed) |
| `1` | One or more comparison failures |
| `2` | Configuration / system / report / logging / invalid XPath or MBI ignore config |

## Excel report

Filename pattern:

```text
<base_file_name>_<verification_type>_<timestamp>.xlsx
```

Example: `VerificationReport_GDI_20260730113045.xlsx`

Worksheets:

- `GDI Verification` or `HSAB Verification`
- `Summary`

Detail columns:

1. Verification Type
2. Scenario
3. Run Type
4. Output Type
5. Expected File
6. Actual File
7. Status (`Passed` / `Failed` / `NotVerified`)
8. Issue (includes difference details when content mismatches)
Formatting includes bold headers, frozen top row, auto-filter, wrapped Issue text, and status background colors from YAML.

## Logging

Logging uses the standard library with optional console and rotating file handlers (`RotatingFileHandler`).

Default log folder: `./logs`  
Default log file: `output-verifier.log`

Logged information includes start/end, version, resolved config, discovery counts, current scenario/files, comparison results, warnings, parsing failures, summary counts, and exit code. Full file content is not logged; long field values are truncated.

## Development setup

Requirements:

- Python 3.14.5
- `requirements.txt` / `requirements-dev.txt` (no `pyproject.toml` / `setup.py`)

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
set PYTHONPATH=src
```

## Test execution

```bat
set PYTHONPATH=src
python -m pytest tests -v
```

## EXE build steps

```bat
build-exe.cmd
```

The script:

1. Creates/uses `.venv`
2. Installs dependencies
3. Runs pytest and aborts on failure
4. Builds with PyInstaller using `output-verifier.spec`
5. Copies `config.yaml` next to the executable as an **external** file
6. Prints `dist\output-verifier.exe`

Important: `config.yaml` is **not** embedded inside `output-verifier.exe`. Edit the external YAML freely and pass it with `--config`.

Run the built executable:

```bat
dist\output-verifier.exe --config dist\config.yaml --verification-type GDI --expected-parent-folder "H:\ExpectedOutputs" --actual-parent-folder "H:\ActualOutputs"
```
## Troubleshooting

| Problem | Likely cause / fix |
| --- | --- |
| Exit code 2, config not found | Check `--config` path |
| Parent folder does not exist | Set valid Expected/Actual roots in YAML or CLI |
| Invalid XPath | Fix `lh1_xml_paths` / `wex_xml_paths` syntax |
| Invalid MBI position | Use positive one-based integers only |
| No scenarios discovered | Confirm run folders (`current`/`pre`/`prepre`/`hold`) and output folders |
| Unexpected Failed for datetime | Filenames are matched after replacing 14-digit datetime with `<datetime>` |
| Import errors in development | Ensure `PYTHONPATH=src` |

## Known limitations

- Record order is assumed identical; files are compared by position, not by business keys
- Only the first two content differences are reported per file pair
- Files are read only from the output folder itself (no recursive subfolder comparison)
- First version supports GDI and HSAB only
- Whitespace-only XML text between child elements is treated as insignificant formatting; meaningful leaf text is compared exactly and is not trimmed

## How to add a future TPA

1. Add a `VerificationType` enum value in `constants.py`
2. Define filename patterns and an `OutputFolderProfile` / `TpaProfile`
3. Register the profile in `TPA_PROFILES`
4. Extend `IgnoreRulesConfig` and YAML `ignore_rules` as needed
5. Add worksheet naming in `excel_reporter.py` if required
6. Add focused unit tests for discovery, matching, and comparison

Keep the design as a simple internal registry. Do not introduce a plugin framework unless requirements expand significantly.

## Windows CMD examples

```bat
REM GDI verification
set PYTHONPATH=src
python -m output_verifier ^
  --config "config.yaml" ^
  --verification-type "GDI" ^
  --expected-parent-folder "H:\ExpectedOutputs" ^
  --actual-parent-folder "H:\ActualOutputs"

REM HSAB verification with report and log overrides
python -m output_verifier ^
  --config "config.yaml" ^
  --verification-type "HSAB" ^
  --expected-parent-folder "H:\ExpectedOutputs" ^
  --actual-parent-folder "H:\ActualOutputs" ^
  --report-output-folder "H:\Reports" ^
  --log-level "DEBUG"
```

## Project layout

```text
output-verifier/
├── src/output_verifier/
├── tests/
├── config.yaml
├── requirements.txt
├── requirements-dev.txt
├── output-verifier.spec
├── build-exe.cmd
├── run-output-verifier.cmd
├── .gitignore
└── README.md
```
