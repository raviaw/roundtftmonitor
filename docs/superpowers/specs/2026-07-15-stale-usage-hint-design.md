# Stale-usage hint on the SESSION/WEEK page

## Problem

The Claude usage (session/week %) readout goes dark for long stretches. Root
cause (confirmed 2026-07-15 from `roundtft-monitor.log`): the host cannot refresh
the OAuth token itself — it only *reads* `accessToken` from `.credentials.json`
and depends on Claude Code (or the desktop app) being alive to keep it fresh.
When nothing refreshes it (overnight / long idle), the access token dies, every
usage probe fails (a clean ~4×`401` then ~4×`429` cycle — 429 is the shared
rate-limiter refusing before auth; 401 is the dead token), and the board grays
the numbers with no explanation. It self-heals the moment Claude Code refreshes
the token (observed: 14 h of failures ended at a success the instant a session
resumed).

We are **not** adding self-refresh (risk: rotating the refresh token could break
Claude Code's own login). Instead: make the grayed-out state *actionable*.

## Change (firmware-only, `firmware/monitor/monitor.ino`)

No host change; the token flow is untouched. Reuse the existing staleness
signal: `usageage` > `USAGE_STALE_SEC` (900 s) → `!usageFresh`.

On **page 1 (SESSION/WEEK)** only, when we have usage values but they are stale,
`drawCenter` renders a compact "stale card" in the 104×104 center sprite instead
of the normal big-number + period-bar layout:

- Six Font2 lines, ~17 px pitch (fits 104 px, no overlap):
  1. `SESSION` (label gray)
  2. `NN%`     (last session value, **gray** — frozen reading stays obvious)
  3. `WEEK`    (label gray)
  4. `NN%`     (last week value, gray)
  5. `OPEN CLAUDE` (**amber** `0xFD40`) — the fix
  6. `STALE Nh` / `STALE Nm` (amber) — how long it's been frozen
- Period bars and history backdrop are suppressed in this state (both are
  meaningless once the values are frozen).

Rings on page 1 already gray when stale (`sFresh`/`wFresh` == false) — unchanged.
Pages 0 and 2 are unchanged (still just gray); the actionable text lives on the
dedicated usage page.

### Why "OPEN CLAUDE" is correct for both 401 and 429

Even in the 429 stretches the blocker is the dead token; recovery came from the
refresh, not from the rate limit clearing. So the remedy is the same regardless
of the last error code — no need for the host to distinguish them, hence no
protocol change.

### Age formatting

From `usageAgeTarget` (seconds): `< 5400 s` → `STALE %dm` (rounded minutes),
else `STALE %dh` (rounded hours).

## Implementation notes

- Add `static const uint16_t AMBER = 0xFD40;` (= `color565(255,170,0)`, the same
  amber as `zoneColor`'s mid band).
- Extend `drawCenter(...)` with two trailing optional params
  `const char* hint1=nullptr, const char* hint2=nullptr`. When `hint1` is set
  (and not `waiting`), draw the stale card branch; otherwise the existing layout.
- In the `page == 1` render path, when `(sOk || wOk) && !usageFresh`, build the
  age string and call `drawCenter(..., "OPEN CLAUDE", ageStr)`; else call as today.
- `waiting` still takes precedence inside `drawCenter` (shows WAITING FOR DATA).

## Out of scope

- Host token self-refresh (deferred; carries login-corruption risk).
- Distinguishing 401 vs 429 on the display.
