# host — PC monitor agent

Streams **CPU%** and **RAM%** to the round display over USB-serial (COM5).

## Requirements
- Python 3 (using `C:\Python314`)
- `pyserial`, `psutil` — install with: `pip install pyserial psutil`
  (already installed to `E:\dev\pip`; the launcher sets `PYTHONPATH` accordingly)

## Run
```
run-monitor.bat            # auto-detect the board's COM port
run-monitor.bat COM5       # or force a port
```
Or directly:
```
set PYTHONPATH=E:\dev\pip
python pc_monitor.py
```

Leave it running; the board shows "WAITING FOR PC" until lines arrive, then the
gauges track CPU/RAM. Stop with Ctrl+C. It auto-reconnects if the board resets.

## Cost on the PC
One Python process polling perf counters once/second — negligible CPU, ~20 MB RAM,
no kernel driver, no admin. (CPU/GPU *temperatures* would need LibreHardwareMonitor;
intentionally not used here.)

## Add "Claude usage" later
1. Fill in `get_claude_usage()` in `pc_monitor.py` to return a number.
2. It auto-appends `claude=<n>` to each line.
3. Add a widget for the `claude` key in `../firmware/monitor/monitor.ino`
   (see the EXTENSION POINT comment).

## Auto-start on login (optional)
Put a shortcut to `run-monitor.bat` in the Startup folder
(`shell:startup`), or create a Task Scheduler task at logon.
