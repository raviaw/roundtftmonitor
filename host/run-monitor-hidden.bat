@echo off
REM Background launch of the roundtft monitor with NO console window.
REM Uses pythonw.exe (windowless) and appends output to a rotating-ish log.
REM Invoked by the scheduled task via monitor-launch.vbs (see install-startup.ps1).
setlocal
set PYTHONPATH=E:\dev\pip
"C:\Python314\pythonw.exe" "%~dp0pc_monitor.py" %* >> "%LOCALAPPDATA%\roundtft-monitor.log" 2>&1
