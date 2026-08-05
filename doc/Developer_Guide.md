# ClaimsXO / EnrollmentXO Output Verifier — Developer Guide

**Version:** 1.0.0  
**Package:** `output_verifier`  
**Audience:** New developers joining the project  

This guide explains the full solution: business purpose, architecture, folder/file rules, comparison logic, configuration, packaging, and how to extend the code safely.

---

## 1. Purpose

QA regression runs produce **Expected Output** and **Actual Output** trees for **ClaimsXO** or **EnrollmentXO**.  
This utility does **not** execute QA. It verifies that Actual files match Expected files for a supported solution + TPA pair.

| Solution | Verification types |
| --- | --- |
| ClaimsXO | GDI, HSAB |
| EnrollmentXO | ABG, GDI, HSAB |

It:

1. Discovers scenario / run / output folders under both roots  
2. Builds a union inventory (Expected-only, Actual-only, and shared)  
3. Matches files by **normalized filename identity** (14-digit datetime / runtime timestamp ignored)  
4. Compares content with format-specific comparators  
5. Applies YAML ignore rules (nested by solution + verification type)  
6. Writes an Excel report and a timestamped log  
7. Prints a console summary and returns an exit code  

---

## 2. High-level architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ CLI (__main__.py / cli.py)                                       │
│  - parse args                                                    │
│  - load + validate config                                        │
│  - setup logging                                                 │
│  - run VerificationService                                       │
│  - write Excel report                                            │
│  - print summary / exit code                                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│ VerificationService                                              │
│  - build_scenario_inventory                                      │
│  - for each discovered output: match files → compare → ReportRow │
└───────┬─────────────────┬──────────────────┬────────────────────┘
        │                 │                  │
        ▼                 ▼                  ▼
 Folder discovery    File matcher      Comparators
 (run/output dirs)   (identity ID)     XML / CSV / MBI / DelimitedText
        │                 │                  │
        └─────────────────┴──────────────────┘
                          │
                          ▼
                 ExcelReporter + Logging
```

### Design principles used in the codebase

- Clean, readable Python with type hints and dataclasses  
- One responsibility per module  
- Stable solution/TPA/filename/run rules live in **Python** (`constants.py`), not YAML  
- Only volatile settings (paths, ignore lists, colors, log level) live in YAML  
- No plugin framework — simple `SOLUTION_PROFILES` registry  
- Comparators never print; only CLI summary uses `print`  
- Config YAML is **external** to the `.exe`  

---

## 3. Repository layout

```text
App/
├── src/output_verifier/          # Main package
│   ├── __main__.py               # Entry point
│   ├── cli.py                    # argparse
│   ├── config.py                 # validators + ConfigurationError
│   ├── config_loader.py          # YAML → ResolvedConfig
│   ├── constants.py              # enums, patterns, TPA profiles
│   ├── models.py                 # dataclasses
│   ├── folder_discovery.py
│   ├── file_matcher.py
│   ├── verification_service.py   # orchestrator
│   ├── logging_setup.py
│   ├── comparators/
│   │   ├── base_comparator.py    # Protocol
│   │   ├── xml_comparator.py
│   │   ├── csv_comparator.py
│   │   ├── mbi_comparator.py
│   │   └── delimited_text_comparator.py
│   ├── reporting/
│   │   └── excel_reporter.py
│   └── utilities/
│       ├── filename_utils.py
│       └── path_utils.py
├── tests/                        # pytest
├── doc/                          # This documentation
├── config.yaml                   # Runtime config (project root)
├── requirements.txt
├── requirements-dev.txt
├── output-verifier.spec
├── build-exe.cmd
├── run-output-verifier.cmd
└── README.md
```

There is **no** `pyproject.toml` / `setup.py`. Development uses `PYTHONPATH=src`.

---

## 4. End-to-end runtime flow

### 4.1 Entry

```bat
set PYTHONPATH=src
python -m output_verifier --config config.yaml ...
```

or frozen:

```bat
output-verifier.exe --config config.yaml ...
```

`--config` defaults to `config.yaml` next to the executable (frozen) or in the current directory (source).

### 4.2 Steps inside `run()` (`__main__.py`)

1. Parse CLI arguments  
2. `load_resolved_config(...)` — CLI overrides YAML; validate folders  
3. Derive:
   - `immediate_parent = actual_parent_folder.name`  
     Example: `...\GDI\20260612_000022_fullrun` → `20260612_000022_fullrun`
   - `timestamp_token = execution_start.strftime(timestamp_format)` typically `%Y%m%d%H%M%S`
4. `setup_logging(...)` → creates  
   `VerificationLog_<solution>_<type>_<immediate_parent>_<timestamp>.Log` under `logging.output_folder`
5. `VerificationService(resolved).run()` → `(report_rows, ExitCode)`
6. `ExcelReporter.write_report(...)` → creates  
   `VerificationReport_<solution>_<type>_<immediate_parent>_<timestamp>.xlsx` under `report.output_folder`
7. Print console summary  
8. Return exit code  

### 4.3 Exit codes

| Code | Enum | Meaning |
| --- | --- | --- |
| 0 | `ExitCode.SUCCESS` | No `Failed` rows (`Passed` / `NotVerified` allowed) |
| 1 | `ExitCode.COMPARISON_FAILURE` | One or more `Failed` rows |
| 2 | `ExitCode.SYSTEM_ERROR` | Config/logging/I/O/invalid XPath/unhandled system error |

Malformed content in one file is a **comparison failure (1)**, not a system error. Processing continues for other files.

---

## 5. Business logic (core domain)

### 5.1 Supported solutions, TPAs, and outputs

Profiles live in `constants.py` as `SOLUTION_PROFILES` (`get_solution_profile(solution, verification)`).

#### ClaimsXO — GDI

| Output folder | Files | Comparator | Ignore config key |
| --- | --- | --- | --- |
| `LH1` | `GDI_LH1_<datetime>.xml`, `GDI_LH1_MMS_…`, `GDI_LH1_FLORES_…`, `GDI_LH1_HNE_…`, `GDI_REGEN_LH1_…`, `GDI_REPROCESS_LH1_…`, `GDI_REPROCESS_LH1_MMS_…`, `GDI_REPROCESS_LH1_FLORES_…`, `GDI_REPROCESS_LH1_HNE_…` | XML | `ignore_rules.ClaimsXO.GDI.lh1_xml_paths` |
| `manual` | `GDI_MANUAL_<datetime>.csv`, `GDI_REPROCESS_MANUAL_<datetime>.csv` | CSV | `manual_csv_columns` |
| `manual` | `GDI_MANUAL_PATIENT_<datetime>.csv`, `GDI_REPROCESS_MANUAL_PATIENT_<datetime>.csv` | CSV | `patient_manual_csv_columns` |
| `ALG` | `LumeLight.ClaimFeed.<datetime>.mbi` | MBI | `mbi_field_positions` |

#### ClaimsXO — HSAB

| Output folder | Files | Comparator | Ignore config key |
| --- | --- | --- | --- |
| `WEX` | `HB1_HSAB_CLAIMS_<datetime>.xml` | XML | `ignore_rules.ClaimsXO.HSAB.wex_xml_paths` |
| `WEX` | `HB2_HSAB_CLAIMS_<datetime>.xml` | XML | same |

#### EnrollmentXO — ABG

| Output folder | Files | Comparator | Ignore config key |
| --- | --- | --- | --- |
| `alegeus` | `Export_<runtime>_….mbi` | DelimitedText (comma, no header) | `alegeus_mbi_field_positions` |
| `reports` | `ExceptionReport_<runtime>_….csv`, `ChangeReport_<runtime>_….csv` | DelimitedText (comma, header) | `report_csv_columns` |

#### EnrollmentXO — GDI

| Output folder | Files | Comparator | Ignore config key |
| --- | --- | --- | --- |
| `WexHealth` | `GDI_WEXHealth_<runtime>.txt` | DelimitedText (pipe, no header) | `wexhealth_field_positions` |
| `reports` | `GDI_ChangeReport_…_<runtime>.csv`, `GDI_ExceptionReport_…_<runtime>.csv` | DelimitedText (comma, header) | `report_csv_columns` |

#### EnrollmentXO — HSAB

| Output folder | Files | Comparator | Ignore config key |
| --- | --- | --- | --- |
| `HSABEnrollmentImport` | `{rest}_<runtime>.txt` | DelimitedText (comma, no header) | `enrollment_import_field_positions` |
| `reports` | HSAB change/exception CSVs with runtime token | DelimitedText (comma, header) | `report_csv_columns` |

Important:

- HB1 must **never** match HB2 (different normalized identities)  
- `GDI_MANUAL` must **never** match `GDI_MANUAL_PATIENT`  
- ClaimsXO datetime / EnrollmentXO runtime timestamps are exactly **14 digits**: `yyyyMMddHHmmss`  

### 5.2 Folder structure and discovery

Logical layout under Expected and Actual parent folders:

```text
<scenario_path>\<run_type>\<output_type>\files...
```

Supported run folders (case-insensitive; reported lower-case):

- `current`
- `pre`
- `prepre`
- `hold`

Example:

```text
test_aggregation\3\pre\LH1\GDI_LH1_20260730110000.xml
```

Report fields:

- Scenario: `test_aggregation\3`  
- Run Type: `pre`  
- Output Type: `LH1`  

Discovery rules (`folder_discovery.py`):

1. Recursively scan for directories named like a supported run folder.  
2. Everything before the run folder (relative to the configured parent) is the scenario path.  
3. Only supported output folders **directly under** the run folder are used.  
4. Only files **directly under** the output folder are compared (no recursive subfolders).  
5. Only files **directly under** the output folder are compared (no recursive subfolders).  
6. Unsupported extensions are ignored. Extensions are solution-specific: ClaimsXO `.xml`/`.csv`/`.mbi`; EnrollmentXO `.mbi`/`.txt`/`.csv` (case-insensitive).  
7. Inventory is the **union** of Expected and Actual scenario keys.

### 5.3 Filename matching

Do **not** compare full filenames when datetime / runtime timestamp differs.

**ClaimsXO** normalized identity replaces the 14-digit datetime with `<datetime>`:

```text
GDI_LH1_20260730110000.xml  →  GDI_LH1_<datetime>.xml
```

**EnrollmentXO** uses named capture groups and replaces the runtime token with `<runtime_timestamp>` while preserving the rest of the identity (e.g. `Export_<runtime_timestamp>_{rest}.mbi`).

| Original | Identity |
| --- | --- |
| `GDI_LH1_20260730110000.xml` | `GDI_LH1_<datetime>.xml` |
| `HB1_HSAB_CLAIMS_20260730110000.xml` | `HB1_HSAB_CLAIMS_<datetime>.xml` |

Matching algorithm (`file_matcher.py`):

1. Classify each file with the TPA profile rule for that output type.  
2. Group by normalized identity.  
3. Sort each group by original filename (case-insensitive).  
4. Pair Expected[i] with Actual[i].  
5. Unpaired files become missing/unexpected rows.  
6. If counts differ for an identity, also add a `File count mismatch` row.

If extension is supported but pattern is invalid → Failed with  
`Unsupported or invalid filename pattern`.

### 5.4 Record-order assumption

- Record/element/row order is assumed identical between Expected and Actual.  
- **No** key-based matching.  
- **No** sorting of records inside files.  
- Compare by position only.

### 5.5 Status rules

| Situation | Status | Typical Issue |
| --- | --- | --- |
| Actual-only scenario/run/output | Failed | Unexpected scenario exists only in Actual Outputs |
| Expected-only scenario/run/output | Failed | Expected scenario missing in Actual Outputs |
| Both sides have no supported files | NotVerified | No files available for verification |
| Expected file missing | Failed | Expected file missing |
| Unexpected actual file | Failed | Unexpected actual file |
| File count mismatch | Failed | File count mismatch. Expected: X, Actual: Y |
| Invalid filename pattern | Failed | Unsupported or invalid filename pattern |
| Content differs after ignores | Failed | XML/CSV/MBI content mismatch (+ difference details) |
| Content equal after ignores | Passed | (empty) |

`Passed` requires Expected found, Actual found, identity match, and content match after ignore rules.

### 5.6 Issue text formatting

Content failures put differences **inside** the `Issue` column (Difference 1/2 columns were removed):

```text
XML content mismatch
Difference 1: /LH1StandardClaimsExchange/@FileDateTime: Attribute value mismatch. ...
Difference 2: ...
```

Maximum **two** content differences per file pair (`MAX_REPORTED_DIFFERENCES = 2`).

---

## 6. Comparators

All implement the `FileComparator` protocol:

```python
compare(expected_path, actual_path, options: ComparisonOptions) -> ComparisonResult
```

### 6.1 XML (`XmlComparator`)

- Uses **lxml** structural comparison (not plain text).  
- Ignores indentation / line endings / attribute order.  
- Preserves element order and meaningful text (no trimming of meaningful values).  
- Whitespace-only text between child elements is treated as insignificant formatting.  
- Namespaces matter; URI differences remain meaningful unless ignored.  

**Ignore paths:**

1. Apply configured XPath to Expected and Actual before compare.  
2. If a simple absolute path like `/LH1StandardClaimsExchange/@CreatedDateTime` finds nothing (common with default namespaces), the comparator rewrites it to a namespace-tolerant form:

```text
/*[local-name()='LH1StandardClaimsExchange']/@CreatedDateTime
```

3. XPath not found in a file → debug/warning, not a failure.  
4. Invalid XPath syntax → configuration/system error (exit 2).  

Difference types include: Element missing/unexpected, Element name mismatch, Text mismatch, Attribute missing/unexpected/value mismatch, Child count mismatch.

### 6.2 CSV (`CsvComparator`)

- Uses Python `csv` module (handles quoted commas, escaped quotes).  
- Header defines layout (not hard-coded columns).  
- Compares header count/names/order, row count/order, field values as strings.  
- Does **not** trim values; leading/trailing spaces are significant.  
- Excel-style row numbering: header = row 1, first data = row 2.  
- Ignored columns removed by exact header name (case-sensitive). Missing configured column → warning.

### 6.3 MBI (`MbiComparator`)

- Delimiter `|`  
- No header/trailer  
- Trailing delimiter is significant (`A|B|C` ≠ `A|B|C|`)  
- Blank fields `||` matter  
- Leading/trailing spaces matter  
- Duplicate records keep original positions  
- Blank lines are not silently discarded  
- Ignored fields use **one-based** positions from YAML  

---

## 7. Configuration

### 7.1 Precedence

1. CLI argument  
2. YAML value  
3. Application default (`DEFAULT_REPORT` / `DEFAULT_LOGGING` in `config_loader.py`)

### 7.2 Current `config.yaml` shape

```yaml
solution_type: ClaimsXO   # or EnrollmentXO
verification_type: GDI    # ClaimsXO: GDI/HSAB | EnrollmentXO: ABG/GDI/HSAB
expected_parent_folder: "..."
actual_parent_folder: "..."

report:
  output_folder: "./reports"
  base_file_name: "VerificationReport"
  include_solution_type: true
  include_verification_type: true
  include_timestamp: true
  timestamp_format: "%Y%m%d%H%M%S"
  status_colors:
    passed: "#C6EFCE"
    failed: "#FFC7CE"
    not_verified: "#FFEB9C"

logging:
  level: INFO
  log_to_console: true
  log_to_file: true
  output_folder: "./logs"
  max_bytes: 10485760
  backup_count: 5

ignore_rules:
  ClaimsXO:
    GDI:
      lh1_xml_paths: [...]
      manual_csv_columns: [...]
      patient_manual_csv_columns: [...]
      mbi_field_positions: [...]
    HSAB:
      wex_xml_paths: [...]
  EnrollmentXO:
    ABG:
      alegeus_mbi_field_positions: []
      report_csv_columns: []
    GDI:
      wexhealth_field_positions: []
      report_csv_columns: []
    HSAB:
      enrollment_import_field_positions: []
      report_csv_columns: []
```

Legacy top-level `ignore_rules.GDI` / `ignore_rules.HSAB` still loads for ClaimsXO and logs a deprecation warning.

### 7.3 Validation highlights

- `solution_type` must be `ClaimsXO` or `EnrollmentXO`  
- `verification_type` must be allowed for that solution  
- Parent folders must exist and be directories at runtime  
- Report/log folders must be creatable  
- Status colors must be `#RRGGBB`  
- Log level must be a valid logging level name  
- XPath ignore lists must be syntactically valid  
- Field positions must be positive integers (duplicates de-duplicated with warning)  

### 7.4 What must stay in Python (not YAML)

Supported TPAs, output folders, extensions, filename patterns, datetime format, run folder names, format mappings, and comparator behavior.

---

## 8. Reporting and logging artifacts

### Report filename

```text
VerificationReport_<solution-type>_<verification-type>_<immediate-actual-parent>_<yyyyMMddHHmmss>.xlsx
```

Example:

```text
VerificationReport_ClaimsXO_GDI_20260612_000022_fullrun_20260730113045.xlsx
```

Location: `report.output_folder`

Worksheets:

- `{Solution} {Verification} Verification` (e.g. `ClaimsXO GDI Verification`)  
- `Summary`  

Detail columns:

1. Solution Type  
2. Verification Type  
3. Scenario  
4. Run Type  
5. Output Type  
6. Expected File  
7. Actual File  
8. Status  
9. Issue  

Difference details are embedded in Issue (no separate Difference 1/2 columns).

### Log filename

```text
VerificationLog_<solution-type>_<verification-type>_<immediate-actual-parent>_<yyyyMMddHHmmss>.Log
```

Location: `logging.output_folder`  
Handler: `RotatingFileHandler` using `max_bytes` / `backup_count`.

Report and log share the same run timestamp taken at process start.

---

## 9. Data model map

Key dataclasses (`models.py`):

| Model | Role |
| --- | --- |
| `ResolvedConfig` | Fully resolved runtime config |
| `ReportConfig` / `LoggingConfig` / `IgnoreRulesConfig` | Config sections |
| `ScenarioKey` | scenario + run + output identity |
| `DiscoveredOutput` | folders + file lists for one key |
| `FileIdentity` | classified file with normalized name |
| `MatchedFilePair` | expected/actual pair for compare |
| `ComparisonOptions` | ignore lists passed to comparator |
| `ComparisonDifference` / `ComparisonResult` | compare outcome |
| `ReportRow` | one Excel row |
| `ExecutionSummary` | counts + paths + exit code |

Enums (`constants.py`): `SolutionType`, `VerificationType`, `OutputType`, `RunType`, `VerificationStatus`, `FileFormat`, `ExitCode`, `DifferenceType`.

---

## 10. How to develop locally

### Setup

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
set PYTHONPATH=src
```

### Run tests

```bat
set PYTHONPATH=src
python -m pytest tests -v
```

### Run utility

```bat
python -m output_verifier --config config.yaml --solution-type ClaimsXO --verification-type GDI ^
  --expected-parent-folder "H:\...\ExpectedOutput\ClaimsXO\GDI" ^
  --actual-parent-folder "H:\...\ActualOutput\ClaimsXO\GDI\20260612_000022_fullrun"

python -m output_verifier --config config.yaml --solution-type EnrollmentXO --verification-type ABG ^
  --expected-parent-folder "H:\...\ExpectedOutput\EnrollmentXO\ABG" ^
  --actual-parent-folder "H:\...\ActualOutput\EnrollmentXO\ABG\<run_folder>"
```

Or use `run-output-verifier.cmd`.

### Build executable

```bat
build-exe.cmd
```

This creates/uses `.venv`, installs deps, runs pytest (stops on failure), builds with PyInstaller, and copies `config.yaml` next to `dist\output-verifier.exe` (YAML is **not** embedded).

---

## 11. How to add a future TPA / solution profile

Keep it simple — extend the registry; do not invent a plugin system.

1. Add enum value(s) to `SolutionType` / `VerificationType` / `OutputType` as needed  
2. Add filename patterns / `FilenameRule` entries (set delimiter, header, identity flags)  
3. Create `SolutionProfile` with `OutputFolderProfile`s  
4. Register in `SOLUTION_PROFILES` and update `allowed_verification_types`  
5. Extend `IgnoreRulesConfig` + nested YAML `ignore_rules` + config loader  
6. Wire comparator selection in `VerificationService` if a new `FileFormat` is needed  
7. Add discovery/matching/comparison tests  

---

## 12. Common troubleshooting for developers

| Symptom | Likely cause |
| --- | --- |
| `--config` required / missing | Old exe before default config; pass `--config config.yaml` or rebuild |
| XML date ignore not applied | Default namespace; current code rewrites simple absolute paths via `local-name()` |
| Still Failed after date ignore | Other fields differ (e.g. CXC ID / CustomProperties) — check Issue text |
| No scenarios found | Parent path wrong, or run/output folder names unsupported |
| Exit code 2 | YAML/XPath/parent folder/logging/report I/O problem |
| Import errors in IDE/tests | `PYTHONPATH=src` not set |

---

## 13. Test map

| Test module | Covers |
| --- | --- |
| `test_config_loader.py` | YAML load/validation/overrides |
| `test_folder_discovery.py` | Scenario/run/output discovery |
| `test_file_matcher.py` | Normalized identity matching |
| `test_xml_comparator.py` | XML equality/diffs/namespaces/ignores |
| `test_csv_comparator.py` | CSV parsing/comparison/ignores |
| `test_mbi_comparator.py` | MBI delimiter/fields/ignores |
| `test_verification_service.py` | Orchestration statuses/exit codes |
| `test_excel_reporter.py` | Report naming + sheets |
| `test_logging_setup.py` | Log naming + file creation |
| `test_enrollment_config.py` | Nested ignore_rules + solution/verification pairs |
| `test_enrollment_discovery.py` | EnrollmentXO folders/extensions/identity |
| `test_enrollment_verification.py` | EnrollmentXO end-to-end compare/report rows |

---

## 14. Coding standards for contributors

Follow the project rules already used in source:

- Meaningful names (no cryptic abbreviations)  
- Type hints; dataclasses where suitable; enums for fixed values  
- `pathlib` instead of string path joins  
- Logging in library code; `print` only for CLI summary/errors  
- Docstrings on public classes/functions  
- No TODO placeholders for core behavior  
- Do not hard-code machine-specific paths in library modules  
- Keep ignoreable volatile data in YAML; keep stable rules in Python  

---

## 15. Mental model for debugging a Failed row

1. Read Scenario / Run / Output / Expected / Actual / Issue from Excel.  
2. If Issue is scenario-level (missing/unexpected scenario) → check folder tree.  
3. If Issue is file missing/unexpected/count → check filename patterns and datetime identities.  
4. If Issue is content mismatch → open both files and inspect Difference lines.  
5. Decide whether difference is a real defect or should be ignored via YAML.  
6. For XML ignores, confirm XPath (prefer simple absolute paths; namespace rewrite is automatic for simple forms).  
7. Re-run and confirm Passed.

For API-level details of every function, continue with [Function_Guide.md](Function_Guide.md).
