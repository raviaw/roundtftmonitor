#!/usr/bin/env python3
"""
Host agent for the roundtft PC + Claude monitor.

Streams to the ESP32-2424S012 over USB-serial, one line per update:
    cpu=37.5 ram=61.2 sess=26.0 week=56.0
    proc=chrome:8.43:12.5|Code:6.10:3.0|...      (top-7 by memory; <=7 items)

- cpu / ram  : PC CPU% and RAM% via psutil (no driver, no admin)
- sess / week: Claude Code 5-hour session% and 7-day week% from the (UNDOCUMENTED)
               OAuth usage endpoint, using the token Claude Code already stores
               in ~/.claude/.credentials.json. Refreshed at most once per minute.
- proc       : top-7 processes by memory as name:memGB:cpu items, '|'-separated.
               memGB = working set in GiB; cpu = share of the whole machine (%).
               One NtQuerySystemInformation call snapshots all processes (~7 ms,
               ~0 CPU); psutil is the per-pid fallback (~1 s) if that ever fails.
               Runs on a background thread so a scan never blocks the per-second
               CPU/RAM stream.

Deps: pyserial, psutil   (pip install pyserial psutil)  -- usage uses stdlib only.
Run:  python pc_monitor.py            # auto-detects the board's COM port
      python pc_monitor.py COM5       # or force a port
"""
import json
import os
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone

# The autostart task launches pythonw.exe directly (no PYTHONPATH), so make the
# custom pip target importable here (override with ROUNDTFT_PIP). No-op if the
# packages are already importable / already on sys.path.
_PIP = os.environ.get("ROUNDTFT_PIP", r"E:\dev\pip")
if _PIP and os.path.isdir(_PIP) and _PIP not in sys.path:
    sys.path.insert(0, _PIP)

import psutil
import serial
from serial.tools import list_ports

# --- Fast top-process scan via the native process snapshot -------------------
# One NtQuerySystemInformation(SystemProcessInformation) call returns name,
# working-set memory, and CPU times for EVERY process in a single syscall (~7 ms,
# ~0 CPU). The psutil path needs an OpenProcess per pid instead (~900 ms, ~1 core
# of kernel time). We use this when it loads cleanly and fall back to psutil if
# the (undocumented) struct ever fails to line up on some Windows build.
try:
    import ctypes

    _ntdll = ctypes.WinDLL("ntdll")

    class _UNICODE_STRING(ctypes.Structure):
        _fields_ = [("Length", ctypes.c_ushort),
                    ("MaximumLength", ctypes.c_ushort),
                    ("Buffer", ctypes.c_void_p)]

    class _SPI(ctypes.Structure):           # SYSTEM_PROCESS_INFORMATION (x64)
        _fields_ = [
            ("NextEntryOffset", ctypes.c_ulong),
            ("NumberOfThreads", ctypes.c_ulong),
            ("WorkingSetPrivateSize", ctypes.c_longlong),
            ("HardFaultCount", ctypes.c_ulong),
            ("NumberOfThreadsHighWatermark", ctypes.c_ulong),
            ("CycleTime", ctypes.c_ulonglong),
            ("CreateTime", ctypes.c_longlong),
            ("UserTime", ctypes.c_longlong),        # 100 ns units, cumulative
            ("KernelTime", ctypes.c_longlong),      # 100 ns units, cumulative
            ("ImageName", _UNICODE_STRING),
            ("BasePriority", ctypes.c_long),
            ("UniqueProcessId", ctypes.c_void_p),
            ("InheritedFromUniqueProcessId", ctypes.c_void_p),
            ("HandleCount", ctypes.c_ulong),
            ("SessionId", ctypes.c_ulong),
            ("UniqueProcessKey", ctypes.c_size_t),
            ("PeakVirtualSize", ctypes.c_size_t),
            ("VirtualSize", ctypes.c_size_t),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),    # bytes; matches psutil rss
        ]

    _NtQSI = _ntdll.NtQuerySystemInformation
    _NtQSI.restype = ctypes.c_ulong
    _NtQSI.argtypes = [ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong,
                       ctypes.POINTER(ctypes.c_ulong)]
    _SYSTEM_PROCESS_INFORMATION = 5
    _STATUS_INFO_LEN_MISMATCH = 0xC0000004
    _HAVE_NT = True
except Exception:
    _HAVE_NT = False

ESP_VID = 0x303A
ESP_PID = 0x1001
BAUD = 115200
INTERVAL = 1.0          # seconds between updates (also the CPU sample window)
PROC_REFRESH = 2.0      # seconds between scans on the fast (ctypes) path
PROC_REFRESH_SLOW = 15.0  # back off to this if we fall back to the psutil path
PROC_COUNT = 7          # how many processes the bars view shows
_NCPU = psutil.cpu_count() or 1
# Latest top-process list, published by the background scanner thread. Replacing
# the whole list is atomic under the GIL, so the main loop reads it lock-free.
_proc_items: list = []

# Are we attached to a real console? Under the autostart task we run as pythonw.exe
# with no console, so sys.stdout is None -> _TTY is False. In that case capture the
# connect/error lines in a small logfile (the per-second data line stays suppressed
# below, so it never grows unbounded). Interactive runs print live and write no file.
_TTY = bool(getattr(sys.stdout, "isatty", lambda: False)())
if not _TTY:
    try:
        _logdir = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        sys.stdout = sys.stderr = open(
            os.path.join(_logdir, "roundtft-monitor.log"), "a", buffering=1, encoding="utf-8")
    except Exception:
        pass

# --- Claude usage (undocumented endpoint; may change/break without notice) ---
CRED_PATH = os.path.expanduser("~/.claude/.credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
USAGE_REFRESH = 300.0   # seconds; query Claude limits once every 5 minutes
SESSION_PERIOD = 5 * 3600        # 5-hour rolling window
WEEK_PERIOD = 7 * 24 * 3600      # nominal 7-day window (tune if it resets sooner)
_usage = {"sess": None, "week": None, "sessp": None, "weekp": None,
          "sessh": None, "weekh": None, "ts": 0.0}


def _remaining_seconds(resets_at):
    if not resets_at:
        return None
    try:
        reset = datetime.fromisoformat(resets_at)
        return max(0.0, (reset - datetime.now(timezone.utc)).total_seconds())
    except Exception:
        return None


def _period_progress(resets_at, period_sec):
    """Fraction (0..100) of the window already elapsed: 100 = about to reset."""
    rem = _remaining_seconds(resets_at)
    return None if rem is None else max(0.0, min(100.0, (1.0 - rem / period_sec) * 100.0))


def _hours_left(resets_at):
    rem = _remaining_seconds(resets_at)
    return None if rem is None else rem / 3600.0


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
        _usage["sessh"] = _hours_left(fh.get("resets_at"))
        _usage["weekh"] = _hours_left(sd.get("resets_at"))
    except Exception as e:
        print(f"usage fetch failed: {e}", flush=True)  # keep last known values
    _usage["ts"] = now
    return _usage


def _san(name: str) -> str:
    """Trim a process name for the display: drop the .exe, strip the field
    delimiters (':' '|') and any non-printable bytes, cap at 12 chars."""
    if name.lower().endswith(".exe"):
        name = name[:-4]
    name = "".join(c for c in name if 32 < ord(c) < 127 and c not in ":|")
    return name[:12] or "?"


_TOTAL_RAM = psutil.virtual_memory().total
_BYTES_PER_GB = 1073741824.0  # GiB -- what Windows labels "GB"
_TOTAL_GB = _TOTAL_RAM / _BYTES_PER_GB
_prev_cpu: dict = {}        # pid -> cumulative (user+kernel) CPU, 100 ns units
_prev_cpu_ts = 0.0          # monotonic time of the previous fast scan


def _scan_fast() -> list:
    """Top PROC_COUNT by memory via one NtQuerySystemInformation call (~7 ms,
    ~0 CPU). memGB = working set in GiB; cpu% = share of the whole machine,
    derived from the user+kernel CPU-time delta since the previous scan (so the
    first scan reads 0 until there are two points to diff)."""
    global _prev_cpu, _prev_cpu_ts
    size = 512 * 1024
    while True:
        buf = (ctypes.c_byte * size)()
        need = ctypes.c_ulong(0)
        st = _NtQSI(_SYSTEM_PROCESS_INFORMATION, buf, size, ctypes.byref(need))
        if st == 0:
            break
        if st == _STATUS_INFO_LEN_MISMATCH:        # snapshot grew; enlarge + retry
            size = max(need.value + 65536, size * 2)
            continue
        raise OSError(f"NtQuerySystemInformation -> {st:#010x}")

    now = time.monotonic()
    dt = (now - _prev_cpu_ts) if _prev_cpu_ts else 0.0
    base, off = ctypes.addressof(buf), 0
    cur_cpu, rows = {}, []
    while True:
        spi = _SPI.from_address(base + off)
        ws = spi.WorkingSetSize
        if ws > 0:
            pid = spi.UniqueProcessId or 0
            if spi.ImageName.Buffer and spi.ImageName.Length:
                name = ctypes.wstring_at(spi.ImageName.Buffer, spi.ImageName.Length // 2)
            else:
                name = "?"
            cput = spi.UserTime + spi.KernelTime          # 100 ns units, cumulative
            cur_cpu[pid] = cput
            cpu = 0.0
            if dt > 0:
                prev = _prev_cpu.get(pid)
                if prev is not None:
                    cpu = max(0.0, (cput - prev) / 1e7 / (dt * _NCPU) * 100.0)
            rows.append((_san(name), ws / _BYTES_PER_GB, cpu))   # memory in GiB
        if spi.NextEntryOffset == 0:
            break
        off += spi.NextEntryOffset

    _prev_cpu, _prev_cpu_ts = cur_cpu, now
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows[:PROC_COUNT]


def _scan_psutil() -> list:
    """Fallback: top PROC_COUNT by memory via psutil. Correct everywhere but
    costs an OpenProcess per pid (~1 s, ~1 core of kernel time on a busy box),
    so the scanner backs off to PROC_REFRESH_SLOW when it has to use this."""
    rows = []
    # process_iter caches Process objects across calls, so cpu_percent() returns
    # a proper delta over the refresh interval; ['attrs'] batches via oneshot().
    for p in psutil.process_iter(["name", "memory_percent", "cpu_percent"]):
        try:
            info = p.info
            mem = info.get("memory_percent") or 0.0
            if mem <= 0.0:
                continue
            cpu = (info.get("cpu_percent") or 0.0) / _NCPU
            memgb = mem / 100.0 * _TOTAL_GB
            rows.append((_san(info.get("name") or "?"), memgb, cpu))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows[:PROC_COUNT]


def _proc_scanner() -> None:
    """Background loop publishing the latest top-process list. Uses the fast
    native scan; if that ever raises (struct mismatch on some Windows build) it
    latches onto the psutil fallback for the rest of the run. Off the main loop
    either way, so a scan never stalls the per-second CPU/RAM/usage stream.
    Daemon thread -- dies with the process."""
    global _proc_items
    use_nt = _HAVE_NT
    while True:
        slow = not use_nt
        try:
            _proc_items = _scan_fast() if use_nt else _scan_psutil()
        except Exception as e:
            if use_nt:
                print(f"fast proc scan failed ({e}); falling back to psutil", flush=True)
                use_nt = False
            try:
                _proc_items = _scan_psutil()
                slow = True
            except Exception as e2:
                print(f"proc scan failed: {e2}", flush=True)
        time.sleep(PROC_REFRESH_SLOW if slow else PROC_REFRESH)


def build_line() -> str:
    cpu = psutil.cpu_percent(interval=INTERVAL)   # blocks INTERVAL secs; paces the loop
    ram = psutil.virtual_memory().percent
    parts = [f"cpu={cpu:.1f}", f"ram={ram:.1f}"]
    u = get_claude_usage()
    for key in ("sess", "week", "sessp", "weekp", "sessh", "weekh"):
        if u[key] is not None:
            parts.append(f"{key}={u[key]:.1f}")
    line = " ".join(parts) + "\n"
    procs = _proc_items                       # snapshot the latest scan (lock-free)
    if procs:
        line += "proc=" + "|".join(f"{n}:{m:.2f}:{c:.1f}" for n, m, c in procs) + "\n"
    return line


def main() -> None:
    forced = sys.argv[1] if len(sys.argv) > 1 else None
    psutil.cpu_percent()   # prime the CPU counter
    threading.Thread(target=_proc_scanner, daemon=True).start()  # top-procs, off the hot path

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
            if _TTY:
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
