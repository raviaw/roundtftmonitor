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
- Task action runs **`C:\Python314\pythonw.exe pc_monitor.py` directly** (no wrapper) so
  `Stop-ScheduledTask` actually kills it — a `wscript→cmd→pythonw` chain leaves an
  unkillable grandchild. pythonw = no window; logs to `%LOCALAPPDATA%\roundtft-monitor.log`.
- No shell env, so `pc_monitor.py` self-bootstraps: adds `E:\dev\pip` to `sys.path`
  (override `ROUNDTFT_PIP`) and, when not a TTY, opens that logfile itself. Per-second
  data line is suppressed off-console (only connect/error events logged).
- Task uses **no execution time limit** (default 3-day limit would kill the forever-loop) and
  triggers at the interactive logon (needs the user session for COM + `.credentials.json`).
- **Before flashing:** `Stop-ScheduledTask -TaskName 'RoundTFT Monitor'` (it holds COM5);
  resume with `Start-ScheduledTask`. Remove with `host\uninstall-startup.ps1`.
- A monitor can **detach from the task and survive `Stop-ScheduledTask`** (seen 2026-07-16:
  a 27 h-old orphan held COM5 *and* double-polled usage, feeding the 429s). `Stop` only
  kills instances the scheduler still tracks. If COM5 gives `PermissionError` after a
  stop, check for strays: `Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'"`
  → `Stop-Process -Id <pid> -Force`. Expect exactly **one** pythonw.

## Claude usage (session/week %)
- No official API. Read it from the **undocumented** `GET https://api.anthropic.com/api/oauth/usage`
  (NOT claude.ai — that 403s). Headers: `Authorization: Bearer <token>`,
  `anthropic-beta: oauth-2025-04-20`, `anthropic-version: 2023-06-01`.
- Token = `claudeAiOauth.accessToken` from `~/.claude/.credentials.json` (re-read each
  call). Response: `five_hour.utilization` (session%), `seven_day.utilization` (week%).
  Polled every 15 min. May break without notice.
- **accessToken lives only ~8 h and Claude Code alone refreshes it.** That was the real
  cause of "usage stopped showing": an idle day → 401 forever until you next opened
  Claude Code. The interleaved 429s were just the endpoint throttling *dead-token*
  retries — they read like a rate-limit bug for weeks but never were. Don't re-debug
  the 429s; check the token first (`expiresAt` vs now).
- The host now runs the **refresh_token grant itself** — `POST https://api.anthropic.com/v1/oauth/token`
  `{grant_type, refresh_token, client_id: 9d1c250a-e61b-44d9-88ed-5944d1962f5e}` — so usage
  now survives ~9 days without Claude Code (`refreshTokenExpiresAt`), not 8 h.
- **The refresh token rotates**: the new one MUST be written back to `.credentials.json`
  or Claude Code is stranded on a spent token (so "refresh in memory only" is not an
  option). `_save_creds()` re-reads → merges → keeps a `.bak` → `os.replace()` atomically.
  Guards: skip if the file was written <120 s ago (Claude Code is live — let it drive),
  ≥60 s between our own attempts, and a `400/401` whose on-disk refreshToken has since
  changed = a benign race with Claude Code, not a dead login.
- Token-endpoint hosts differ from the usage host: `platform.claude.com` **403s
  (Cloudflare error 1010)** on urllib's default User-Agent, `console.anthropic.com` now
  **404s**, and **api.anthropic.com works bare**. We use api.anthropic.com + a real UA.

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
- **`Serial.printf` blocks the loop** on the native USB-CDC: the host holds COM5 open
  but never reads it, so a print stalls for ~2 s once the TX FIFO fills. That froze the
  touch poll after every gesture → the unpolled CST816 fired a phantom-touch burst
  (the real cause of the "ghost taps/holds," not a panel defect; the debounce/lockout
  band-aids only masked it). Fix: **`Serial.setTxTimeoutMs(0)` in `setup()`** so unread
  output drops instead of blocking. Keep any per-loop serial output non-blocking.
