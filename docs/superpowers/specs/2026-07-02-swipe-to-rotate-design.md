# Swipe-to-rotate gesture — design

**Date:** 2026-07-02
**Status:** approved (approach A), implementing
**File:** `firmware/monitor/monitor.ino` (touch handling only)

## Problem / motivation
Orientation is currently changed by a 0.6–1.5 s **hold** (`handleTouch`). That hold is:
- fragile (a timing band wedged between tap and brightness),
- the prolonged touch we believe **poisons the CST816 baseline** and triggers the
  post-rotate phantom-flip bursts (see commit 2c64e3c), which forced a 2 s lockout,
- one-directional (cycles 0→1→2→3→0 only).

Replace it with a **horizontal swipe**, which is distinct, intuitive, bidirectional,
and immune to phantom center-touches (a phantom jitters in place; it never travels).
Removing the hold also removes the baseline-poisoning trigger.

## Gesture ladder (after)
| Gesture | Detection | Action |
|---|---|---|
| **Swipe L / R** | net horizontal travel ≥ `SWIPE_MIN_PX`, and \|dx\| > \|dy\| | rotate 90° (R = +1, L = −1) |
| **Tap** | released < `BRIGHT_MS`, not a swipe | next page |
| **Hold ≥ `BRIGHT_MS`** | low travel, held past 1.5 s | brightness mode → drag → release saves |

The 0.6–1.5 s rotate band and `LONG_MS` are removed. Any non-swipe release before the
brightness threshold is a page tap.

## Detection design
- `readTouchY` → `readTouch(int& sx, int& sy)`: returns the touch point mapped to
  **on-screen** coordinates for the current rotation (both axes, not just vertical),
  so "horizontal" always means horizontal *to the user* regardless of orientation.
  Screen mapping (panel x,y 0..239):
  - rot0: sx=x, sy=y · rot1: sx=y, sy=239−x · rot2: sx=239−x, sy=239−y · rot3: sx=239−y, sy=x
  (sy matches the existing, working `vy` mapping; sx derived from the same convention.)
- Track `tpDownX/Y` at the press edge and `tpLastX/Y` on every good read.
- At the release edge, `dx = tpLastX − tpDownX`, `dy = tpLastY − tpDownY` (net
  displacement — robust to jitter). Classify swipe first, else fall through to
  tap/hold. Direction constant `SWIPE_RIGHT_IS_CW` makes flipping trivial if it
  feels backwards.

## Tuning
- `SWIPE_MIN_PX = 50`. A deliberate face swipe on the 240 px panel travels 100–200 px;
  a tap < ~15 px; phantom net displacement stays small (jitter doesn't accumulate in
  one direction). 50 px sits with wide margin between tap and swipe.
- Log each rotate as `swipe dx=.. dy=.. -> rotate N` for on-device verification/tuning;
  trim the log once calibrated.

## Lockout
- Swipe-rotate and tap → short `TAP_LOCK_MS` (150 ms lift-off bounce).
- Brightness release (still a long hold) → keep `ROT_LOCK_MS` for baseline recovery.
- The 2 s post-rotate dead-time is gone — rotate is now snappy.

## Risks
- Swipe/tap threshold needs a real-swipe sanity check (logged).
- Direction mapping across rotations must be consistent (flip constant if needed).
- Muscle-memory change from the old hold; net an upgrade.

## Out of scope
Hardware CST816 gesture register (approach B), double-tap (C), on-screen arrow hint
(possible later polish).
