@echo off
title Sanjana OMR Application Launcher
echo Starting Sanjana OMR Application...
"C:\Users\sriha\AppData\Local\Programs\Python\Python313\python.exe" index.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Press any key to exit...
    pause >nul
)
