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

Leave it running; the board shows "WAITING FOR PC" until lines arrive, then the
gauges track CPU/RAM. Stop with Ctrl+C. It auto-reconnects if the board resets.

## Cost on the PC
One Python process polling perf counters once/second — negligible CPU, ~20 MB RAM,
no kernel driver, no admin. (CPU/GPU *temperatures* would need LibreHardwareMonitor;
intentionally not used here.)

## Start automatically at logon
Run once from any PowerShell (no admin needed):
```
powershell -ExecutionPolicy Bypass -File install-startup.ps1
```
This registers a hidden scheduled task **`RoundTFT Monitor`** that launches the
agent at every logon and restarts it if it crashes. Output goes to
`%LOCALAPPDATA%\roundtft-monitor.log`.

| Do this | Command |
|---|---|
| Stop it (e.g. **before flashing** — it holds COM5) | `Stop-ScheduledTask -TaskName 'RoundTFT Monitor'` |
| Start it again | `Start-ScheduledTask -TaskName 'RoundTFT Monitor'` |
| Remove autostart | `powershell -ExecutionPolicy Bypass -File uninstall-startup.ps1` |

The launcher hardcodes `C:\Python314\pythonw.exe` and `PYTHONPATH=E:\dev\pip`
(a scheduled task can't inherit your shell's env) — edit `run-monitor-hidden.bat`
if those paths change.

## Troubleshooting

**Board / display shows "WAITING FOR PC" and the agent logs `board not found
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
