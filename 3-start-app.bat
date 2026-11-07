@echo off
setlocal EnableExtensions
title Step 3 of 5 - Start the app
cd /d "%~dp0"

echo ============================================================
echo   Interior Design Platform   -   STEP 3 of 5
echo   Start the app. Two black windows will open. KEEP THEM OPEN.
echo   Your browser will open by itself in about 10 seconds.
echo ============================================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo   The app is not installed yet. Run 2-install.bat first.
    goto end
)

echo Starting the data service...
start "IDP backend - keep this window open" cmd /k "cd /d "%~dp0backend" && set APP_ADMIN_EMAIL=admin@example.com&& set APP_ADMIN_PASSWORD=passw0rd123&& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Starting the screens...
start "IDP frontend - keep this window open" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Waiting for the app to wake up...
"%SystemRoot%\System32\timeout.exe" /t 10 /nobreak >nul

echo Opening the browser...
start "" "http://localhost:5173"

echo.
echo ------------------------------------------------------------
echo   The app should now be open in your browser.
echo   If the page says it cannot reach the server, wait 20 more
echo   seconds and press F5 in the browser.
echo.
echo   Test accounts are in TESTING.md, section 3.
echo   When you finish, run 5-stop-app.bat.
echo ------------------------------------------------------------
echo.

:end
if /i not "%1"=="nopause" pause