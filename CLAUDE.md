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
- Sized for the unit **in its plastic shell** (measured 2026-08-13): a rounded
  pebble **45 mm** at the equator × **11 mm** thick, USB-C **on the rim**, with a
  **42 mm** glass. An earlier 40.5 mm outer figure was WRONG — don't reinstate it.
- Only **1.5 mm of plastic rim** (⌀45 vs ⌀42) for the lip to land on: `aperture`
  43.0 = 0.5 mm clear of the glass + 1.0 mm of ledge. Holes print undersize, so
  the glass side keeps the clearance. `stand.scad` **asserts**
  `glass_d < aperture < disc_d` and `disc_t > ring_d` — keep those.
- Stock **ESP32-2424S012C** published specs (hold caliper readings against these):
  bare PCB **38.5 x 37.0**, active display **32.4 dia** (CANNOT vary), panel
  outline ~35.6 x 38.1, cased dia **"about 42"** (CNX). The 42 mm glossy front is
  NOT the LCD -- the panel is only ~35.6, so its outer mm are case plastic.
- **Unresolved**: published cased dia ~42 vs measured 45 (equator) / 42 (front
  face). If the true widest is 42, the 43 mm lip bore exceeds the shell and it
  falls through. Gauge: calipers at 43.0 must NOT pass the shell.
- Seat = straight bore + front lip, NOT a cone: a cone's grip depends on the
  shell's rim curvature, which can't be measured off a photo. USB-C exits
  **sideways** (`port_angle`, default 90 = viewer's left) — a right-angle plug
  needs ~10 mm radially and at the bottom that lands below the desk.
- Leans back **38°**; `place_z` is **derived** from `tilt` (don't hard-code it —
  leaning moves the ring's lowest edge, which once put the part under the plate).
- **`python stand/verify.py` after ANY change** — ten pass/fail checks (seat
  invariants, single body, sits on the plate, watertight, shell overlap = 0,
  full bed contact). Each one exists because something got past without it.
- Cut the seat **after** unioning base+leg, or the base slab fills the pocket.
- Slice with `stand/slice.sh` (OrcaSlicer portable at `E:\dev\orcaslicer`); it
  bounds-checks the G-code it emits. Don't hand-write G-code for the K1 Max.
- **Bed adhesion (first print let go, 2026-08-17).** `filament.json` inherits the
  *generic* PLA library, which runs textured PEI at **45 °C / 200 °C** — Creality's
  own PLA is 60/220. That, not the missing brim, is why it unstuck; the fan hitting
  100% at layer 2 finished the job. Now 60 °C bed, 215/210 nozzle,
  `close_fan_the_first_x_layers` 3, first layer 0.25 mm at 30 mm/s, and an
  **8 mm `outer_only` brim** at gap 0. Verify in the G-code, never the UI.
- **`outer_brim_only` is not a valid OrcaSlicer 2.4.2 value** — it silently falls back
  to `auto_brim`, which then decides this part needs no brim. It's **`outer_only`**.
  `gcode_check.py` now measures the brim out of the `;TYPE:Brim` toolpaths (and parses
  `G2/G3`, which arc fitting means it was ignoring entirely).
- `stand/stand_K1Max_project.3mf` is the **profile in portable form** (model + all
  settings in `Metadata/project_settings.config`) — Creality Print / Creality Opus /
  Orca / Bambu are all the same slicer's forks and open it ready to slice.
  `stand.3mf` is plain geometry; don't mix them up. `slice.sh` regenerates both.
- **`rim_r` is derived, not eyeballed** — `(disc_d - glass_d)/2`. The glass sits
  on the front face, so the face must be >= `glass_d`; a guessed 3.5 implied a
  38 mm face under a 42 mm glass and every interference check ran against an
  impossible shape. Sanity-check any shell stand-in against the measurements.
- `fit` is **0.8** on the 45 mm bore: FDM shrinks holes, and 0.5 left zero
  clearance at 0.5 mm of shrink (shell won't enter). Shrink moves the lip
  *toward* the glass, so the 0.5 mm glass gap is the shrink budget; the ledge
  only gains.
- Known limit: at 15% infill the part is ~12 g (~42 g with the display) and
  **slides at ~31 g of finger force** — a swipe is 100-300 g. Feet or more
  infill, not geometry.
- **A `z=0` bounding box does NOT mean it sits flat.** The base plate floated
  2.25 mm for months (lifted by `base_t/2` though `rrect()` already builds up
  from 0) with the part balanced on one small bar — bbox still read 0. Check by
  intersecting a thin bottom slab and comparing to the base footprint area.

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
