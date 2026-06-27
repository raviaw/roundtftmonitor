#!/usr/bin/env python3
"""
Host agent for the roundtft PC + Claude monitor.

Streams to the ESP32-2424S012 over USB-serial, one line per update:
    cpu=37.5 ram=61.2 sess=26.0 week=56.0

- cpu / ram  : PC CPU% and RAM% via psutil (no driver, no admin)
- sess / week: Claude Code 5-hour session% and 7-day week% from the (UNDOCUMENTED)
               OAuth usage endpoint, using the token Claude Code already stores
               in ~/.claude/.credentials.json. Refreshed at most once per minute.

Deps: pyserial, psutil   (pip install pyserial psutil)  -- usage uses stdlib only.
Run:  python pc_monitor.py            # auto-detects the board's COM port
      python pc_monitor.py COM5       # or force a port
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

import psutil
import serial
from serial.tools import list_ports

ESP_VID = 0x303A
ESP_PID = 0x1001
BAUD = 115200
INTERVAL = 1.0          # seconds between updates (also the CPU sample window)

# --- Claude usage (undocumented endpoint; may change/break without notice) ---
CRED_PATH = os.path.expanduser("~/.claude/.credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
USAGE_REFRESH = 300.0   # seconds; query Claude limits once every 5 minutes
SESSION_PERIOD = 5 * 3600        # 5-hour rolling window
WEEK_PERIOD = 7 * 24 * 3600      # nominal 7-day window (tune if it resets sooner)
_usage = {"sess": None, "week": None, "sessp": None, "weekp": None, "ts": 0.0}


def _period_progress(resets_at, period_sec):
    """Fraction (0..100) of the window already elapsed: 100 = about to reset."""
    if not resets_at:
        return None
    try:
        reset = datetime.fromisoformat(resets_at)
        remaining = (reset - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, min(100.0, (1.0 - remaining / period_sec) * 100.0))
    except Exception:
        return None


def find_port() -> str | None:
    for p in list_ports.comports():
        if p.vid == ESP_VID and p.pid == ESP_PID:
            return p.device
    return None


def _read_token() -> str | None:
    try:
        with open(CRED_PATH, encoding="utf-8") as fh:
            return json.load(fh)["claudeAiOauth"]["accessToken"]
    except Exception:
        return None


def get_claude_usage() -> dict:
    """Usage % + period-progress % from the OAuth endpoint, cached for
    USAGE_REFRESH. Returns last known values (or None) on failure -- never raises."""
    now = time.monotonic()
    if _usage["ts"] and now - _usage["ts"] < USAGE_REFRESH:
        return _usage

    token = _read_token()  # re-read each time: Claude Code rewrites it on refresh
    if not token:
        _usage["ts"] = now
        return _usage

    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "anthropic-version": "2023-06-01",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        fh = data.get("five_hour") or {}
        sd = data.get("seven_day") or {}
        _usage["sess"]  = fh.get("utilization")
        _usage["week"]  = sd.get("utilization")
        _usage["sessp"] = _period_progress(fh.get("resets_at"), SESSION_PERIOD)
        _usage["weekp"] = _period_progress(sd.get("resets_at"), WEEK_PERIOD)
    except Exception as e:
        print(f"usage fetch failed: {e}", flush=True)  # keep last known values
    _usage["ts"] = now
    return _usage


def build_line() -> str:
    cpu = psutil.cpu_percent(interval=INTERVAL)   # blocks INTERVAL secs; paces the loop
    ram = psutil.virtual_memory().percent
    parts = [f"cpu={cpu:.1f}", f"ram={ram:.1f}"]
    u = get_claude_usage()
    for key in ("sess", "week", "sessp", "weekp"):
        if u[key] is not None:
            parts.append(f"{key}={u[key]:.1f}")
    return " ".join(parts) + "\n"


def main() -> None:
    forced = sys.argv[1] if len(sys.argv) > 1 else None
    psutil.cpu_percent()   # prime the CPU counter

    ser = None
    while True:
        try:
            if ser is None or not ser.is_open:
                port = forced or find_port()
                if not port:
                    print("board not found (303A:1001); retrying...", flush=True)
                    time.sleep(2)
                    continue
                ser = serial.Serial(port, BAUD, timeout=1)
                print(f"connected on {port}", flush=True)

            line = build_line()
            ser.write(line.encode("ascii"))
            print(line.strip(), flush=True)
        except (serial.SerialException, OSError) as e:
            print(f"serial error: {e}; reconnecting...", flush=True)
            try:
                if ser:
                    ser.close()
            except Exception:
                pass
            ser = None
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nstopping", flush=True)
            break


if __name__ == "__main__":
    main()
