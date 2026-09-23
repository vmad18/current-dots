"""Share scan colors across monitors; rotate every 30 seconds while working."""
import math
import random
import time

COLORS = ("orange", "blue", "purple")
LEASE_SECONDS = 3.0
SWITCH_SECONDS = 30.0

def transition(state, watcher, working, now, choose=random.choice):
    """Pure state update, called under the tracker's existing shared lock."""
    if not isinstance(state, dict):
        state = {}
    old = state.get("watchers", {})
    watchers = {
        key: dict(value) for key, value in (old.items() if isinstance(old, dict) else ())
        if isinstance(value, dict)
        and isinstance(value.get("seen_at"), (int, float))
        and 0 <= now - value["seen_at"] < LEASE_SECONDS
    }
    was_active = any(value.get("working") for value in watchers.values())
    color = state.get("color")
    changed_at = state.get("changed_at")
    watchers[watcher] = {"working": bool(working), "seen_at": now}
    if working and (not was_active or color not in COLORS):
        color = choose(COLORS)
        changed_at = now
    elif working:
        if (not isinstance(changed_at, (int, float))
                or not math.isfinite(changed_at) or changed_at > now):
            changed_at = now
        elif now - changed_at >= SWITCH_SECONDS:
            color = choose(tuple(candidate for candidate in COLORS if candidate != color))
            changed_at = now
    if not any(value.get("working") for value in watchers.values()):
        changed_at = None
    return {"version": 2, "color": color, "changed_at": changed_at,
            "watchers": watchers}, color if working else None

class ScanPalette:
    def __init__(self, path, lock, load, write):
        self.path, self.lock, self.load, self.write = path, lock, load, write
        self.watcher = str(time.time_ns())
        self.working = None
        self.color = None
        self.refresh_at = 0.0

    def color_for(self, working):
        now = time.monotonic()
        if working != self.working or now >= self.refresh_at:
            with self.lock():
                state, self.color = transition(
                    self.load(self.path, {}), self.watcher, working, now)
                self.write(self.path, state)
            self.working = working
            self.refresh_at = now + 0.75
        return self.color if working else None
