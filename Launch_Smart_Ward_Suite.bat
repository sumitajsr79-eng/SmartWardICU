@echo off
title D.B.M.S. Smart Ward ICU & Home Care Suite Launcher
cls
echo ============================================================
echo   D.B.M.S. SMART WARD ICU & HOME CARE TELEMETRY SUITE
echo ============================================================
echo.
echo  [1] Launch Unified Suite Launcher (Recommended)
echo  [2] Launch Smart Ward Monitor (Live Dashboard)
echo  [3] Launch Emergency Location & Automated Dispatcher
echo  [4] Launch BOTH Monitor + Dispatcher Simultaneously
echo  [5] Exit
echo.
set /p choice="Select an option (1-5): "

if "%choice%"=="1" (
    if exist "%~dp0SmartWardLauncher.exe" (
        start "" "%~dp0SmartWardLauncher.exe"
    ) else (
        start "" python "%~dp0smart_ward_launcher.py"
    )
    exit
)
if "%choice%"=="2" (
    if exist "%~dp0SmartWardMonitor.exe" (
        start "" "%~dp0SmartWardMonitor.exe"
    ) else (
        start "" python "%~dp0smart_ward_monitor.py"
    )
    exit
)
if "%choice%"=="3" (
    if exist "%~dp0EmergencyLocationDispatcher.exe" (
        start "" "%~dp0EmergencyLocationDispatcher.exe"
    ) else (
        start "" python "%~dp0emergency_location_dispatcher.py"
    )
    exit
)
if "%choice%"=="4" (
    if exist "%~dp0SmartWardMonitor.exe" (
        start "" "%~dp0SmartWardMonitor.exe"
    ) else (
        start "" python "%~dp0smart_ward_monitor.py"
    )
    if exist "%~dp0EmergencyLocationDispatcher.exe" (
        start "" "%~dp0EmergencyLocationDispatcher.exe"
    ) else (
        start "" python "%~dp0emergency_location_dispatcher.py"
    )
    exit
)
exit
