# Output Verifier (ClaimsXO + EnrollmentXO + TransactionXO)

Python utility that compares **Expected Output** files against **Actual Output** files after a QA regression run, then writes an Excel verification report.

Package name: `output_verifier`  
Main command: `python -m output_verifier --config config.yaml`  
Executable name: `output-verifier.exe`

`--config` defaults to `config.yaml` next to the executable (or in the current folder for source runs).

## Documentation

Detailed developer docs live under [`doc/`](doc/README.md):

- [Developer Guide](doc/Developer_Guide.md) — architecture, business logic, configuration, extending TPAs
- [Function Guide](doc/Function_Guide.md) — module/class/function reference

## Purpose

After QA has already produced Expected and Actual output trees, this tool:

1. Discovers supported scenario / run / output folders
2. Matches expected and actual files by normalized filename identity (datetime/runtime/dynamic ignored)
3. Compares content with format-specific comparators and configured ignore rules
4. Writes an Excel report and prints a console summary
5. Returns an exit code suitable for automation

## Supported solution types

| Solution | Verification types |
| --- | --- |
| **ClaimsXO** | GDI, HSAB |
| **EnrollmentXO** | ABG, GDI, HSAB |
| **TransactionXO** | HSAB |

### ClaimsXO

| Verification type | Output folders | File types |
| --- | --- | --- |
| **GDI** | `LH1`, `manual`, `ALG` | XML, CSV, MBI |
| **HSAB** | `WEX` | XML (`HB1` / `HB2`) |

### EnrollmentXO

| Verification type | Output folders | Comparator |
| --- | --- | --- |
| **ABG** | `alegeus`, `reports` | DelimitedTextComparator (comma MBI / CSV) |
| **GDI** | `WexHealth`, `reports` | DelimitedTextComparator (pipe TXT / CSV) |
| **HSAB** | `HSABEnrollmentImport`, `reports` | DelimitedTextComparator (comma TXT / CSV) |

### TransactionXO

| Verification type | Output folders | Comparator |
| --- | --- | --- |
| **HSAB** | `MDC`, `MDCExceptions` | FixedWidthComparator / CsvComparator |

**MDC** (`HSB_EN_*_Converted.txt`): fixed-width text, line-by-line, spaces preserved, record order enforced. Dynamic middle segment is ignored for matching (`HSB_EN_*_Converted.txt`).

**MDCExceptions**:
- Duplicate Account: `HSB_EN_*_ExceptionDupAcct*.csv` → identity `HSB_EN_*_ExceptionDupAcct*.csv`
- UTP: `HSB_EN_*_ExceptionUTP_*.csv` → identity `HSB_EN_*_ExceptionUTP_*.csv`

These two exception identities never pair with each other. CSV comparison is exact (header + positional rows); long `EN transaction` mismatches report a character position with truncated context.

Ignore rules are grouped by solution and verification type:

```yaml
ignore_rules:
  ClaimsXO:
    GDI: { ... }
    HSAB: { ... }
  EnrollmentXO:
    ABG: { ... }
    GDI: { ... }
    HSAB: { ... }
  TransactionXO:
    HSAB:
      mdc_ignored_character_ranges: []   # e.g. "20-27", "45"
      exception_dup_acct_csv_columns: []
      exception_utp_csv_columns: []
```

Old top-level `ignore_rules.GDI` / `ignore_rules.HSAB` still loads temporarily for ClaimsXO and logs a deprecation warning.

### Supported ClaimsXO GDI files

- `LH1`: `GDI_LH1_<datetime>.xml`, `GDI_LH1_MMS_<datetime>.xml`, `GDI_LH1_FLORES_<datetime>.xml`, `GDI_LH1_HNE_<datetime>.xml`, `GDI_REGEN_LH1_<datetime>.xml`, `GDI_REPROCESS_LH1_<datetime>.xml`, `GDI_REPROCESS_LH1_MMS_<datetime>.xml`, `GDI_REPROCESS_LH1_FLORES_<datetime>.xml`, `GDI_REPROCESS_LH1_HNE_<datetime>.xml`
- `manual`: `GDI_MANUAL_<datetime>.csv`, `GDI_MANUAL_PATIENT_<datetime>.csv`, `GDI_REPROCESS_MANUAL_<datetime>.csv`, `GDI_REPROCESS_MANUAL_PATIENT_<datetime>.csv`
- `ALG`: `LumeLight.ClaimFeed.<datetime>.mbi`, `LumeLight.Reprocess.ClaimFeed.<datetime>.mbi`

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
- Ignore unsupported extensions (ClaimsXO: `.xml`/`.csv`/`.mbi`; EnrollmentXO: `.mbi`/`.txt`/`.csv`)

## YAML configuration

Template: `config.yaml`

Important settings:

- `solution_type`: `ClaimsXO`, `EnrollmentXO`, or `TransactionXO`
- `tpa_id`: allowed for that solution (ClaimsXO: GDI/HSAB; EnrollmentXO: ABG/GDI/HSAB; TransactionXO: HSAB)
- `expected_parent_folder` / `actual_parent_folder`
- `run_folders`: optional comma-separated run folders to compare (`current`, `pre`, `prepre`, `hold`). Empty compares all of them. Matching is case-insensitive. `hold` is only `current\LH1\Hold`, not a folder under `pre` or `prepre`.
- `report.*` report naming, folder, and status colors
- `logging.*` console/file logging with rotation
- `ignore_rules.<Solution>.<Verification>` nested ignore lists

Stable application rules (filename patterns, run folders, extensions, comparators) stay in Python code, not YAML.

### Ignore-rule examples

```yaml
ignore_rules:
  ClaimsXO:
    GDI:
      lh1_xml_paths:
        - "/LH1StandardClaimsExchange/@CreatedDateTime"
      manual_csv_columns:
        - "GeneratedTimestamp"
      patient_manual_csv_columns: []
      mbi_field_positions:
        - 7
    HSAB:
      wex_xml_paths: []
  EnrollmentXO:
    ABG:
      alegeus_mbi_field_positions: []
      report_csv_columns: []
  TransactionXO:
    HSAB:
      mdc_ignored_character_ranges: []
      exception_dup_acct_csv_columns: []
      exception_utp_csv_columns: []
```

Notes:

- XML ignore paths use XPath; invalid XPath is a configuration error (exit code 2)
- CSV ignore columns match header names exactly (case-sensitive)
- Field-position ignores are one-based positive integers
- Legacy top-level `ignore_rules.GDI` / `HSAB` still loads for ClaimsXO with a deprecation warning

## Command-line examples

Development run (from repository root):

```bat
set PYTHONPATH=src
python -m output_verifier --config config.yaml --solution-type ClaimsXO --tpa-id GDI --expected-parent-folder "H:\ExpectedOutputs" --actual-parent-folder "H:\ActualOutputs"

python -m output_verifier --config config.yaml --solution-type EnrollmentXO --tpa-id ABG --expected-parent-folder "H:\Expected" --actual-parent-folder "H:\Actual"

python -m output_verifier --config config.yaml --solution-type TransactionXO --tpa-id HSAB --expected-parent-folder "H:\ExpectedOutputs\TransactionXO\HSAB" --actual-parent-folder "H:\ActualOutputs\TransactionXO\HSAB"
```

Or use the helper script:

```bat
run-output-verifier.cmd --solution-type ClaimsXO --tpa-id GDI --expected-parent-folder "H:\ExpectedOutputs" --actual-parent-folder "H:\ActualOutputs"
```

CLI overrides (override YAML):

- `--config`
- `--solution-type`
- `--tpa-id`
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
VerificationReport_<solution-type>_<verification-type>_<immediate-actual-parent>_<yyyyMMddHHmmss>.xlsx
```

Example actual root:

```text
H:\...\ActualOutput\ClaimsXO\GDI\20260612_000022_fullrun
```

Example report:

```text
VerificationReport_ClaimsXO_GDI_20260612_000022_fullrun_20260730113045.xlsx
```

The report is written under `report.output_folder` from configuration.

Difference details are embedded in **Issue** (no separate Difference 1/2 columns).

Worksheets:

- `ClaimsXO GDI Verification`, `EnrollmentXO ABG Verification`, etc.
- `Summary`

Detail columns:

1. Solution Type
2. Verification Type
3. Scenario
4. Run Type
5. Output Type
6. Expected File
7. Actual File
8. Status (`Passed` / `Failed` / `NotVerified`)
9. Issue (includes difference details when content mismatches)

Formatting includes bold headers, frozen top row, auto-filter, wrapped Issue text, and status background colors from YAML.

## Logging

Logging uses the standard library with optional console and rotating file handlers (`RotatingFileHandler`).

Default log folder: value of `logging.output_folder`  
Default log file pattern:

```text
VerificationLog_<solution-type>_<verification-type>_<immediate-actual-parent>_<yyyyMMddHHmmss>.Log
```

Example:

```text
VerificationLog_ClaimsXO_GDI_20260612_000022_fullrun_20260730113045.Log
```

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
dist\output-verifier.exe --config dist\config.yaml --tpa-id GDI --expected-parent-folder "H:\ExpectedOutputs" --actual-parent-folder "H:\ActualOutputs"
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
  --tpa-id "GDI" ^
  --expected-parent-folder "H:\ExpectedOutputs" ^
  --actual-parent-folder "H:\ActualOutputs"

REM HSAB verification with report and log overrides
python -m output_verifier ^
  --config "config.yaml" ^
  --tpa-id "HSAB" ^
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
