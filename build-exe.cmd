@echo off
setlocal EnableExtensions

REM Build output-verifier.exe after installing dependencies and running tests.

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create virtual environment.
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate virtual environment.
  exit /b 1
)

echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
  echo Dependency installation failed.
  exit /b 1
)

echo Running tests...
set "PYTHONPATH=%ROOT%src"
python -m pytest tests -q
if errorlevel 1 (
  echo Tests failed. Executable build aborted.
  exit /b 1
)

echo Building executable with PyInstaller...
python -m PyInstaller --noconfirm --clean output-verifier.spec
if errorlevel 1 (
  echo PyInstaller build failed.
  exit /b 1
)

set "EXE_PATH=%ROOT%dist\output-verifier.exe"
if not exist "%EXE_PATH%" (
  echo Build completed but executable was not found at %EXE_PATH%
  exit /b 1
)

REM Keep YAML outside the .exe: copy config.yaml next to the executable.
copy /Y "%ROOT%config.yaml" "%ROOT%dist\config.yaml" >nul
if errorlevel 1 (
  echo Failed to copy external config.yaml next to the executable.
  exit /b 1
)

echo.
echo Build successful.
echo Executable : %EXE_PATH%
echo External YAML: %ROOT%dist\config.yaml
echo NOTE: config.yaml is NOT embedded in the .exe. Pass it with --config.
echo.
endlocal
exit /b 0