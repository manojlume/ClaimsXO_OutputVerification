===================
Context
===================
There is a TransactionXO solution used by multiple TPAs. Each TPA can generate different types of output files, and one scenario may generate more than one output file.

Currently, this utility needs to support the following TPA:

	- HSAB

In future, more TPAs may be added.

The QA run is already complete for all test cases. But the outputs have not been verified. Your job is to verify the outputs by comparing the Actual Output files with the Expected Output files for all test cases/scenarios and generate a QA report.

The purpose of this enhancement is to add TransactionXO and HSAB support into the existing Python-based Output Verification utility without affecting the existing ClaimsXO functionality.

The existing utility already supports:

	- ClaimsXO
	  - GDI
	  - HSAB

Do not rewrite or duplicate the existing utility. Review the current implementation and extend the existing architecture, configuration, folder discovery, file matching, comparators, reporting, logging, tests, and Windows executable packaging.


Folder Structure

===================
Expected Output Parent Folder
===================
The configured Expected Output parent folder will contain scenario folders in the following format:

<type>\<run_type>\<output_type>

Rules:

- <type> represents the test scenario path and may contain one or more nested subfolders.
- <run_type> is currently:
  - current
- <output_type> contains the generated output files.
- Supported output folders are:
  - MDC
  - MDCExceptions
- Output files may be:
  - TXT
  - CSV
- Unrelated folders or unsupported files should be ignored.

Example:

test_AllScenarios\current\MDC

test_AllScenarios\current\MDCExceptions

For this example:

- Scenario: test_AllScenarios
- Run Type: current
- Output Type: MDC or MDCExceptions


================
Actual Output Parent Folder
================
The configured Actual Output parent folder will follow the same folder structure:

<type>\<run_type>\<output_type>

Example:

test_AllScenarios\current\MDC

test_AllScenarios\current\MDCExceptions

Rules:

- <type> may contain one or more nested subfolders.
- <run_type> is currently:
  - current
- <output_type> contains the generated Actual Output files.
- Unrelated folders or unsupported files should be ignored.


Supported TPA Output Files

---------
HSAB TPA
---------

TransactionXO HSAB can generate the following output files.

1. MDC Fixed-Width Text File

Output folder: MDC

Supported filename pattern:

HSB_EN_*_Converted.txt

Example:

HSB_EN_2026062401_Converted.txt

The dynamic portion between HSB_EN_ and _Converted.txt should be ignored during filename matching.

The MDC file:

- Is a fixed-width text file.
- Does not contain a header row.
- Does not contain a trailer row.
- Contains one record per physical line.
- Must be compared line by line.


The Expected and Actual MDC files should be compared as follows:

- Compare the line count.
- Compare Expected line 1 with Actual line 1, Expected line 2 with Actual line 2, and so on.
- Compare the line length.
- Do not trim or normalize spaces.
- Do not convert or normalize field values.


MDC ignored character ranges should be configurable in YAML using one-based inclusive positions.

YAML configuration:

mdc_ignored_character_ranges:
  - "36-43"
  - "44-51"

The comparator should skip these character positions in both Expected and Actual lines

Invalid ignored-range configuration should be treated as a configuration error.

MDC difference examples:

- Line count mismatch. Expected: 7, Actual: 6
- Line: 4, length mismatch. Expected: 193, Actual: 192
- Line: 4, Character Position: 68, Expected: "P", Actual: "N"
- Line: 4, Character Range: 68-75, Expected: "POSITIVE", Actual: "NEGATIVE"

Report only the first two content differences in the Excel report.

2. Duplicate Account Exception CSV File

Output folder: MDCExceptions

Supported filename pattern:

HSB_EN_*_ExceptionDupAcct*.csv

Examples:

- HSB_EN_2026062401_AllScenarios_ExceptionDupAcct_20260805103159.csv
- HSB_EN_2026062403_AllExceptions_ExceptionDupAcct_20260805104855.csv

The dynamic sections of the filename should be ignored during filename matching.

The file:

- Uses comma as the delimiter.
- Contains a header row.
- May contain quoted commas.
- May contain escaped double quotes.
- May contain empty values.


Sample header:

SSN,Amount,Description,TransactionCode


3. UTP Exception CSV File

Output folder: MDCExceptions

Supported filename pattern:

HSB_EN_*_ExceptionUTP_*.csv

Examples:

- HSB_EN_2026062401_AllScenarios_ExceptionUTP_20260805103159.csv
- HSB_EN_2026062403_AllExceptions_ExceptionUTP_20260805104855.csv

The dynamic sections of the filename should be ignored during filename matching.

The file:

- Uses comma as the delimiter.
- Contains a header row.
- May contain quoted commas.
- May contain escaped double quotes.
- May contain empty values.

Sample header:

SSN,Amount,EN transaction

The EN transaction column may contain a long fixed-width transaction value with meaningful spaces. Preserve and compare the value exactly.


CSV Comparison Rules

Use the existing CSV comparator

- Compare the header column count.
- Compare header names.
- Compare header order.
- Compare the data-row count.
- Compare rows in the same order.
- Compare corresponding values by column position.
- Compare values exactly as strings.
- Column order matters.
- No Exception CSV columns are ignored by default.

The Duplicate Account and UTP files should use separate YAML ignore-column lists because their layouts are different.

CSV difference examples:

- Row: 2, Column: Amount, Expected: 60.00, Actual: 65.00
- Row: 3, Column: TransactionCode, Expected: 12, Actual: 13
- Header column 3 mismatch. Expected: Description, Actual: ExceptionDescription
- Row count mismatch. Expected: 4, Actual: 3

Filename Matching

Expected and Actual filenames may contain different dynamic values.

The utility should recognize and normalize the following logical filename patterns:

- HSB_EN_*_Converted.txt
- HSB_EN_*_ExceptionDupAcct*.csv
- HSB_EN_*_ExceptionUTP_*.csv
