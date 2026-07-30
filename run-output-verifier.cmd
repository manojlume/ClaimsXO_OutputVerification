@echo off
setlocal EnableExtensions

REM Run the ClaimsXO output verifier using the local source tree.

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHONPATH=%ROOT%src"
set "CONFIG=%ROOT%config.yaml"

if "%~1"=="" (
  python -m output_verifier --config "%CONFIG%"
) else (
  python -m output_verifier --config "%CONFIG%" %*
)

set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
