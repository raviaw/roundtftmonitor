# CLAUDE.md — roundtft

PC + Claude usage monitor on a round ESP32 display. Full design notes in
[PROJECT.md](PROJECT.md); hardware ID in [roundtft-hardware.md](roundtft-hardware.md).

## The device
- Board: **GUITION ESP32-2424S012** — ESP32-C3, 1.28" 240×240 round **GC9A01**
  LCD, **CST816D** touch (I2C 0x15), 4 MB flash, native **USB-Serial/JTAG**.
- Enumerates on Windows as **COM5** (VID 303A / PID 1001). MAC 10:b4:1d:20:45:88.
- No IMU/gyro (confirmed by I2C scan), no PSRAM. ~320 KB usable SRAM.
- Pinout: LCD SCLK=6 MOSI=7 DC=2 CS=10 RST=none BL=3 · Touch SDA=4 SCL=5 INT=0
  RST=1 · BOOT=9 · GPIO8 is the only free pin.

## Build / flash (arduino-cli, no IDE)
- Toolchain lives at `E:\dev\arduino-cli\` (config `arduino-cli.yaml`, data/user dirs there).
- FQBN: **`esp32:esp32:esp32c3:CDCOnBoot=cdc,FlashSize=4M`** — `CDCOnBoot=cdc` is
  required or `Serial` won't appear on COM5 (it'd go to UART0).
- Compile: `arduino-cli compile --fqbn <fqbn> --config-file <cfg> --build-path firmware\monitor\build firmware\monitor`
- Upload: `arduino-cli upload -p COM5 --fqbn <fqbn> --config-file <cfg> --input-dir firmware\monitor\build firmware\monitor`
- **Stop the host agent before flashing** — it holds COM5 (PermissionError/“port busy” otherwise).
  After reset the USB port re-enumerates; a retry usually succeeds.
- Restore stock GUITION demo: `esptool --port COM5 write-flash 0x0 backup-firmware-stock-4MB.bin`.

## Host agent (`host/pc_monitor.py`)
- Streams `cpu= ram= sess= week=` lines to COM5 at 115200 (1 s loop; psutil+pyserial).
- Python is `C:\Python314`; pip installs to **`E:\dev\pip`** (custom target) — run
  scripts with `PYTHONPATH=E:\dev\pip`. Launch via `host\run-monitor.bat`.

## Autostart (Task Scheduler)
- Install: `powershell -ExecutionPolicy Bypass -File host\install-startup.ps1` registers a
  per-user task **`RoundTFT Monitor`** that runs at logon, hidden, and restarts on crash.
- Chain: task → `wscript host\monitor-launch.vbs` (window style 0) → `host\run-monitor-hidden.bat`
  → `pythonw.exe pc_monitor.py`. Logs to `%LOCALAPPDATA%\roundtft-monitor.log`.
- `run-monitor-hidden.bat` hardcodes `C:\Python314\pythonw.exe` + `PYTHONPATH=E:\dev\pip`
  (Task Scheduler can't inherit shell env) — edit it if those paths change.
- Task uses **no execution time limit** (default 3-day limit would kill the forever-loop) and
  triggers at the interactive logon (needs the user session for COM + `.credentials.json`).
- **Before flashing:** `Stop-ScheduledTask -TaskName 'RoundTFT Monitor'` (it holds COM5);
  resume with `Start-ScheduledTask`. Remove with `host\uninstall-startup.ps1`.

## Claude usage (session/week %)
- No official API. Read it from the **undocumented** `GET https://api.anthropic.com/api/oauth/usage`
  (NOT claude.ai — that 403s). Headers: `Authorization: Bearer <token>`,
  `anthropic-beta: oauth-2025-04-20`, `anthropic-version: 2023-06-01`.
- Token = `claudeAiOauth.accessToken` from `~/.claude/.credentials.json` (re-read
  each call; Claude Code refreshes it). Response: `five_hour.utilization` (session%),
  `seven_day.utilization` (week%). Polled every 5 min. May break without notice.

## 3D stand (`stand/`)
- Parametric OpenSCAD tilt cradle (`stand.scad` → `stand.stl`). OpenSCAD portable at
  `E:\dev\openscad\openscad-2021.01\openscad.exe`. Render: `openscad -o stand.stl stand.scad`.
- Render a PNG to inspect headlessly: `openscad -o out.png --viewall --autocenter --camera=0,0,0,90,0,90,0 stand.scad`.
- Fit params to verify with calipers: `disc_d` (40.5), `disc_t` (4.6).

## Gotchas learned
- OpenSCAD CGAL **"Volumes: 2" = one solid + surrounding void = a single body**
  (N disjoint solids → N+1).
- ESP32-C3 USB-Serial-JTAG resets re-enumerate the port, so a captured serial
  handle dies on reset — reopen after flashing/reset.
- Driver chip names (GC9A01/CST816) are compiled register writes, not flash strings.
- **Do not full-screen double-buffer** (a 240×240 `LGFX_Sprite` + `pushSprite`):
  it compiled and `createSprite` succeeded but the panel stayed **blank**. Working
  path = draw rings directly to `tft` + a small 104×104 center sprite for text.
  To avoid the zero-tick flickering, put it in the **gap between rings** (r 91–95)
  where ring fills never repaint it — not on top of a ring.
