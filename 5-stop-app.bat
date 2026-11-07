@echo off
setlocal EnableExtensions
title Step 5 of 5 - Stop the app
cd /d "%~dp0"

echo ============================================================
echo   Interior Design Platform   -   STEP 5 of 5
echo   Close the two black windows and free the ports.
echo ============================================================
echo.

echo Closing the data service on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>nul
    echo   stopped process %%a
)

echo Closing the screens on port 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>nul
    echo   stopped process %%a
)

echo.
echo ------------------------------------------------------------
echo   The app is stopped. Your browser tab will stop responding.
echo   To use it again: 3-start-app.bat, then 4-load-demo-data.bat.
echo ------------------------------------------------------------
echo.

if /i not "%1"=="nopause" pause