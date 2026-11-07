@echo off
setlocal EnableExtensions
title Step 1 of 5 - Check this PC
cd /d "%~dp0"

echo ============================================================
echo   Interior Design Platform   -   STEP 1 of 5
echo   Check that this PC has the three tools the app needs.
echo ============================================================
echo.

set MISSING=0

where git >nul 2>nul
if errorlevel 1 (
    echo   [MISSING] Git
    echo             Get it from https://git-scm.com/download/win
    echo             Install with the default options, then run this file again.
    set MISSING=1
) else (
    for /f "delims=" %%v in ('git --version') do echo   [OK]      %%v
)

where node >nul 2>nul
if errorlevel 1 (
    echo   [MISSING] Node.js
    echo             Get the LTS installer from https://nodejs.org/en/download
    echo             Install with the default options, then run this file again.
    set MISSING=1
) else (
    for /f "delims=" %%v in ('node -v') do echo   [OK]      Node.js %%v
)

where python >nul 2>nul
if errorlevel 1 (
    echo   [MISSING] Python
    echo             Get Python 3.12 from https://www.python.org/downloads/windows/
    echo             IMPORTANT: tick "Add python.exe to PATH" on the first screen.
    set MISSING=1
) else (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
    if errorlevel 1 (
        echo   [TOO OLD] Python is installed but older than 3.10.
        echo             Install Python 3.12 from https://www.python.org/downloads/windows/
        set MISSING=1
    ) else (
        for /f "delims=" %%v in ('python --version') do echo   [OK]      %%v
    )
)

echo.
if "%MISSING%"=="1" (
    echo ------------------------------------------------------------
    echo   One or more tools are missing.
    echo   Install what is listed above, RESTART the PC if asked,
    echo   then double-click this file again until every line is [OK].
    echo ------------------------------------------------------------
) else (
    echo ------------------------------------------------------------
    echo   All three tools are present. You can run 2-install.bat.
    echo ------------------------------------------------------------
)
echo.

if /i not "%1"=="nopause" pause