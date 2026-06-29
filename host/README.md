# host — PC + Claude monitor agent

Streams **CPU%**, **RAM%**, and **Claude session/week usage** to the round display
(**GUITION ESP32-2424S012**) over USB-serial (COM5).

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

Leave it running; the board shows "WAITING FOR DATA" until lines arrive, then the
gauges track CPU/RAM. If the stream stops, the board holds the last values for up
to 10 s before showing "WAITING FOR DATA" again. Stop with Ctrl+C; it
auto-reconnects if the board resets.

When run from a console the agent prints each line live; under the autostart task
(no console) it only logs connect/error events, so the logfile stays small.

## Cost on the PC
One Python process polling perf counters once/second — negligible CPU, ~20 MB RAM,
no kernel driver, no admin. (CPU/GPU *temperatures* would need LibreHardwareMonitor;
intentionally not used here.)

## Start automatically at logon
Run once from any PowerShell (no admin needed):
```
powershell -ExecutionPolicy Bypass -File install-startup.ps1
```
This registers a scheduled task **`RoundTFT Monitor`** that runs `pythonw.exe`
(no window) at every logon and restarts it if it crashes. Output goes to
`%LOCALAPPDATA%\roundtft-monitor.log`.

| Do this | Command |
|---|---|
| Stop it (e.g. **before flashing** — it holds COM5) | `Stop-ScheduledTask -TaskName 'RoundTFT Monitor'` |
| Start it again | `Start-ScheduledTask -TaskName 'RoundTFT Monitor'` |
| Remove autostart | `powershell -ExecutionPolicy Bypass -File uninstall-startup.ps1` |

The task launches `pythonw.exe` **directly** (so `Stop-ScheduledTask` reliably
terminates it — a wrapper chain would leave an unkillable child). The Python path
`C:\Python314\pythonw.exe` is set in `install-startup.ps1`; the package dir
defaults to `E:\dev\pip` in `pc_monitor.py` (override with the `ROUNDTFT_PIP` env
var). Edit those if your paths differ.

## Troubleshooting

**Board / display shows "WAITING FOR DATA" and the agent logs `board not found
(303A:1001); retrying...`** — Windows isn't seeing the device.

1. **Use a real USB *data* cable, not a charge-only one.** This is the most common
   cause: the screen lights up (it has power) but no COM port appears, because the
   cable has no data wires. Swap to a cable you've actually copied files with.
2. Plug into a USB port directly on the PC (not a hub); reseat the cable.
3. Unplug, wait a few seconds, replug — the ESP32-C3's native USB re-enumerates.

Confirm Windows sees it (it should report `VID_303A`, usually on COM5):
```
Get-PnpDevice -PresentOnly | Where-Object InstanceId -match 'VID_303A'
```
The agent matches by USB VID/PID, **not** a fixed COM number, so it connects
automatically even if Windows assigns a different port.
