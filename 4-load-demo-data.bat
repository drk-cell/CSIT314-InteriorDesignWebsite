@echo off
setlocal EnableExtensions
title Step 4 of 5 - Load demo data
cd /d "%~dp0"

echo ============================================================
echo   Interior Design Platform   -   STEP 4 of 5
echo   Put example designers, projects and requests in the app.
echo   Run this AFTER 3-start-app.bat, and only once per start.
echo ============================================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo   The app is not installed yet. Run 2-install.bat first.
    goto end
)

echo Choose the data set:
echo.
echo   [D]  Demo data   3 designers, 8 projects. Fast. Best for a first look.
echo   [B]  Bulk data   20 designers, 100 customers, 100 projects,
echo                    100 quote requests. Takes about 15 seconds.
echo.
choice /c DB /n /m "Press D or B: "
if errorlevel 2 goto bulk
if errorlevel 1 goto demo

:demo
echo.
echo Loading the demo data...
pushd backend
set APP_ADMIN_EMAIL=admin@example.com
set APP_ADMIN_PASSWORD=passw0rd123
".venv\Scripts\python.exe" scripts\seed_demo.py
popd
goto done

:bulk
echo.
echo Loading the bulk data...
pushd backend
set APP_ADMIN_EMAIL=admin@example.com
set APP_ADMIN_PASSWORD=passw0rd123
".venv\Scripts\python.exe" scripts\seed_demo.py
".venv\Scripts\python.exe" scripts\seed_bulk.py
popd
goto done

:done
echo.
echo ------------------------------------------------------------
echo   Data loaded. Go back to the browser and sign in.
echo   Accounts: see TESTING.md, section 3.
echo ------------------------------------------------------------
echo.

:end
if /i not "%1"=="nopause" pause