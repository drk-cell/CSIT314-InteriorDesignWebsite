@echo off
setlocal EnableExtensions
title Step 6 - Load my data files
cd /d "%~dp0"

echo ============================================================
echo   Interior Design Platform   -   STEP 6
echo   Load the CSV files in testing\data.
echo   Run this AFTER 3-start-app.bat.
echo ============================================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo   The app is not installed yet. Run 2-install.bat first.
    goto end
)

if not exist "testing\data\accounts.csv" (
    echo   I cannot find testing\data\accounts.csv
    echo   Check that the four CSV files sit in the testing\data folder.
    goto end
)

echo Files in testing\data:
dir /b "testing\data\*.csv"
echo.

echo Press C to CHECK the files only, or L to LOAD them.
echo.
choice /c CL /n /m "Press C or L: "
if errorlevel 2 goto load
if errorlevel 1 goto check

:check
echo.
echo Checking, nothing will be saved...
"backend\.venv\Scripts\python.exe" backend\scripts\import_data.py --dry-run
goto done

:load
echo.
echo Loading...
"backend\.venv\Scripts\python.exe" backend\scripts\import_data.py
goto done

:done
echo.
echo ------------------------------------------------------------
echo   The summary is above. A report is saved at
echo   testing\data\import-report.txt - send that file back.
echo ------------------------------------------------------------
echo.

:end
if /i not "%1"=="nopause" pause