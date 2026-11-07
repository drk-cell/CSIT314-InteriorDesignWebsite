@echo off
setlocal EnableExtensions
title Step 2 of 5 - Install the app
cd /d "%~dp0"

echo ============================================================
echo   Interior Design Platform   -   STEP 2 of 5
echo   Install the parts the app needs. This takes 2 to 5 minutes.
echo   Leave the window open. Text will scroll; that is normal.
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo   Python is missing. Run 1-check-my-pc.bat first.
    goto end
)
where node >nul 2>nul
if errorlevel 1 (
    echo   Node.js is missing. Run 1-check-my-pc.bat first.
    goto end
)

echo [1/3] Preparing the Python environment...
if not exist "backend\.venv\Scripts\python.exe" (
    python -m venv backend\.venv
    if errorlevel 1 goto failed
) else (
    echo       Already prepared, reusing it.
)

echo [2/3] Installing the backend packages...
"backend\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
"backend\.venv\Scripts\python.exe" -m pip install --quiet -r backend\requirements.txt
if errorlevel 1 goto failed

echo [3/3] Installing the frontend packages...
pushd frontend
call npm install --no-fund --no-audit
if errorlevel 1 (
    popd
    goto failed
)
popd

echo.
echo ------------------------------------------------------------
echo   INSTALL FINISHED.
echo   Next: double-click 3-start-app.bat
echo ------------------------------------------------------------
goto end

:failed
echo.
echo ------------------------------------------------------------
echo   INSTALL STOPPED. Something above failed.
echo   Copy the last 20 lines of this window and send them to the
echo   person who asked you to test.
echo ------------------------------------------------------------
goto end

:end
echo.
if /i not "%1"=="nopause" pause