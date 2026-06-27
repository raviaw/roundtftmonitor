@echo off
REM Launch the roundtft PC monitor host agent.
REM Auto-detects the board's COM port (Espressif 303A:1001).
setlocal
set PYTHONPATH=E:\dev\pip
python "%~dp0pc_monitor.py" %*
