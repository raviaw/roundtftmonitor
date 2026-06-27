# roundtft — PC performance monitor on a round ESP32 display

## Goal
Repurpose the round ESP32 board as a desk **PC performance monitor**.
- Phase 1 metrics: **CPU %** and **RAM %** (zero-driver, lightest on the PC).
- Later: add **Claude usage** and possibly more — protocol is designed to be
  extensible (just add a field + a widget; no rewrite).

## Chosen architecture (decided)
**Wired USB-serial**, because it is both the *lightest on the PC* and the *fastest
to the screen*:
- Host agent on the PC reads only the needed counters and writes one short line
  down **COM5** (USB-CDC). No web server, no network stack, no extra services.
- Firmware on the board parses the line and renders gauges via LovyanGFX.
- CPU%/RAM% come from plain Windows performance counters → no kernel driver,
  no admin. (Temps/GPU would need LibreHardwareMonitor; intentionally skipped.)

Rejected: Wi-Fi+LibreHardwareMonitor (more overhead/jitter) and ESPHome+Home
Assistant (heaviest — needs HA running; slowest refresh).

## The board (confirmed)
**GUITION ESP32-2424S012** — ESP32-C3, 1.28" 240×240 round IPS **GC9A01**,
**CST816D** capacitive touch (I2C 0x15), 4 MB flash, native USB-Serial/JTAG.
Full hardware detail: [roundtft-hardware.md](roundtft-hardware.md).

### Confirmed pinout
| Function | GPIO | | Function | GPIO |
|---|---|---|---|---|
| LCD SCLK | 6 | | Touch SDA (I2C) | 4 |
| LCD MOSI | 7 | | Touch SCL (I2C) | 5 |
| LCD DC | 2 | | Touch INT | 0 |
| LCD CS | 10 | | Touch RST | 1 |
| LCD BL (backlight) | 3 | | BOOT button | 9 |
| LCD RST | none (tied to chip reset) | | **GPIO 8** | free |

Only **GPIO 8** is spare. USB on 18/19, UART0 on 20/21. (Pinout from the
ESP32-2424S012 board docs; being empirically verified by the probe sketch.)

## Toolchain
- **arduino-cli** at `E:\dev\arduino-cli\` (config `arduino-cli.yaml`, data/user dirs there).
- ESP32 Arduino core installed via `core install esp32:esp32`.
- Library: LovyanGFX (GC9A01 driver).
- Board FQBN: `esp32:esp32:esp32c3` with **`CDCOnBoot=cdc`** so `Serial` = USB on COM5.

## Restore the stock GUITION demo anytime
```
esptool --port COM5 write-flash 0x0 backup-firmware-stock-4MB.bin
```
(`backup-firmware-stock-4MB.bin` = full 4 MB dump of the as-shipped firmware.)

## Repo layout
- `backup-firmware-stock-4MB.bin` — as-shipped firmware (do not delete).
- `roundtft-hardware.md` — full chip/flash identification.
- `firmware/probe/probe.ino` — pin-verification probe (backlight blink + GC9A01 test pattern).
- `firmware/monitor/` — (planned) the real CPU/RAM monitor sketch.
- `host/` — (planned) the Windows serial agent that feeds CPU%/RAM%.

## Status
- [x] Identify board + pinout
- [x] Back up stock firmware
- [x] Install arduino-cli + start ESP32 core install
- [x] Write probe sketch
- [x] Compile + flash probe, confirm screen lights up — **CONFIRMED** ("PROBE OK" + sweep, colors correct)
- [x] Build monitor firmware + serial protocol — `firmware/monitor/monitor.ino`
- [x] Build Windows host agent (CPU%/RAM%) — `host/pc_monitor.py` (+ `run-monitor.bat`)
- [x] Flash monitor + run agent — **WORKING** (gauges track live CPU%/RAM%)
- [ ] Add Claude-usage metric (later) — stub at `get_claude_usage()` + EXTENSION POINT in firmware

## Current display
Two pages, **short tap** toggles, **long-press** rotates 90°. The active page is
identified by the center labels (CPU/RAM vs SESS/WEEK).
- **Page 0 (PC):** thick outer ring = CPU%, thick inner ring = RAM%, center
  `CPU%/RAM%`. Two **thin** outer rings hint Claude session/week.
- **Page 1 (Claude):** thick outer = Session (5h)%, thick inner = Week (7d)%,
  center `SESS%/WEEK%`. Two **thin** outer rings hint CPU/RAM.
Colors: green <60, amber 60-85, red >85 (so a near-full red ring = near a limit).
Claude values show `--` if unavailable. "WAITING FOR PC" if no serial.

## Claude usage source
Host reads the OAuth token from `~/.claude/.credentials.json` and GETs the
**undocumented** `https://api.anthropic.com/api/oauth/usage` (`five_hour` /
`seven_day` utilization), **once every 5 minutes**. No official API exists; the
endpoint may break without notice. CPU%/RAM% still update every 1 s.

## Sensors / inputs
- **No IMU / gyroscope** — confirmed by I2C scan (`firmware/i2cscan/`): the only
  device on the bus is **0x15 (CST816 touch)**. No 0x68/0x69/0x6A/0x6B.
- **Touch long-press rotates the view 90°**: hold a finger on the glass for
  >0.6 s and the display turns one quarter-turn (cycles through all 4 orientations).
  One step per press — lift before pressing again. Tunable via `LONG_MS` in
  `firmware/monitor/monitor.ino`.

## Day-to-day use
Run `host/run-monitor.bat` (auto-detects the port). For auto-start, drop a
shortcut to it in `shell:startup`. Board keeps the gauges as long as the agent runs.

## Serial protocol (host -> board)
One line per update, `\n`-terminated, space-separated `key=value` pairs, e.g.:
```
cpu=37.5 ram=61.2
```
Firmware updates known keys and ignores unknown ones, so adding a metric later
(e.g. `claude=...`) needs only a new field on the host + a widget on the board.
Baud 115200 on COM5 (USB-CDC). If no line arrives for ~3 s the board shows
"WAITING FOR PC".
