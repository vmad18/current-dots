#!/usr/bin/env python3
"""Toggle floating while remembering each live window's floating geometry."""

from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


HYPRCTL = "/usr/bin/hyprctl"
TERMINAL_SIZE = (700, 400)
TERMINAL_LEFT_PADDING = 48
TERMINAL_TOP_PADDING = 32
NON_TERMINAL_SCALE = 0.92
MAX_SAVED_WINDOWS = 128

TERMINAL_CLASSES = {
    "alacritty",
    "com.mitchellh.ghostty",
    "foot",
    "footclient",
    "ghostty",
    "kitty",
    "org.wezfurlong.wezterm",
    "wezterm",
}


def run_hyprctl(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [HYPRCTL, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def active_window() -> dict[str, Any]:
    result = run_hyprctl("-j", "activewindow")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "hyprctl activewindow failed")

    data = json.loads(result.stdout)
    return data if isinstance(data, dict) else {}


def window_address(window: dict[str, Any]) -> str:
    address = str(window.get("address") or "")
    if not re.fullmatch(r"0x[0-9A-Fa-f]+", address):
        return ""
    return address


def pair(value: Any, name: str) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"active window has no valid {name}")
    return int(value[0]), int(value[1])


def geometry(window: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int]]:
    return pair(window.get("at"), "position"), pair(window.get("size"), "size")


def is_terminal(window: dict[str, Any]) -> bool:
    classes = {
        str(window.get("class") or "").casefold(),
        str(window.get("initialClass") or "").casefold(),
    }
    return bool(classes & TERMINAL_CLASSES)


def monitor_work_area(window: dict[str, Any]) -> tuple[int, int, int, int] | None:
    result = run_hyprctl("-j", "monitors")
    if result.returncode != 0:
        return None

    try:
        monitors = json.loads(result.stdout)
        monitor_id = int(window.get("monitor", -1))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None

    if not isinstance(monitors, list):
        return None

    for monitor in monitors:
        if not isinstance(monitor, dict) or int(monitor.get("id", -2)) != monitor_id:
            continue

        try:
            x = int(monitor["x"])
            y = int(monitor["y"])
            scale = float(monitor.get("scale", 1)) or 1
            width = round(int(monitor["width"]) / scale)
            height = round(int(monitor["height"]) / scale)
            if int(monitor.get("transform", 0)) % 2:
                width, height = height, width
            reserved = monitor.get("reserved", [0, 0, 0, 0])
            if not isinstance(reserved, list) or len(reserved) != 4:
                raise ValueError("monitor has no valid reserved area")
            left, top, right, bottom = (int(value) for value in reserved)
        except (KeyError, TypeError, ValueError):
            return None

        return (
            x + left,
            y + top,
            max(1, width - left - right),
            max(1, height - top - bottom),
        )

    return None


def initial_float_geometry(
    window: dict[str, Any],
    work_area: tuple[int, int, int, int] | None = None,
) -> tuple[tuple[int, int], tuple[int, int]]:
    (x, y), (width, height) = geometry(window)

    if is_terminal(window):
        new_width, new_height = TERMINAL_SIZE
        if work_area:
            work_x, work_y, work_width, work_height = work_area
            new_x = min(
                work_x + TERMINAL_LEFT_PADDING,
                work_x + max(0, work_width - new_width),
            )
            new_y = min(
                work_y + TERMINAL_TOP_PADDING,
                work_y + max(0, work_height - new_height),
            )
            return (new_x, new_y), (new_width, new_height)
    else:
        new_width = max(1, round(width * NON_TERMINAL_SCALE))
        new_height = max(1, round(height * NON_TERMINAL_SCALE))

    new_x = x + (width - new_width) // 2
    new_y = y + (height - new_height) // 2
    return (new_x, new_y), (new_width, new_height)


def state_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    root = (
        Path(runtime_dir) / "hypr-toggle-floating"
        if runtime_dir
        else Path.home() / ".cache" / "hypr-toggle-floating"
    )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)

    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "default")
    safe_signature = re.sub(r"[^A-Za-z0-9_.-]", "_", signature)
    return root / f"{safe_signature}.json"


def empty_state() -> dict[str, Any]:
    return {"version": 1, "windows": {}}


def load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return empty_state()

    if not isinstance(data, dict) or not isinstance(data.get("windows"), dict):
        return empty_state()
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    windows = state.get("windows", {})
    if isinstance(windows, dict) and len(windows) > MAX_SAVED_WINDOWS:
        newest = sorted(
            windows.items(),
            key=lambda item: float(item[1].get("saved_at", 0))
            if isinstance(item[1], dict)
            else 0,
            reverse=True,
        )[:MAX_SAVED_WINDOWS]
        state["windows"] = dict(newest)

    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(state, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked_state() -> Iterator[dict[str, Any]]:
    path = state_path()
    lock_path = path.with_suffix(path.suffix + ".lock")

    with lock_path.open("a+", encoding="utf-8") as lock:
        lock_path.chmod(0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state(path)
        yield state
        save_state(path, state)


def identity_matches(entry: Any, window: dict[str, Any]) -> bool:
    if not isinstance(entry, dict):
        return False
    try:
        same_pid = int(entry.get("pid", -1)) == int(window.get("pid", -2))
    except (TypeError, ValueError):
        return False
    return same_pid and str(entry.get("initial_class") or "") == str(
        window.get("initialClass") or ""
    )


def saved_geometry(
    entry: dict[str, Any],
) -> tuple[tuple[int, int], tuple[int, int]]:
    return pair(entry.get("at"), "saved position"), pair(entry.get("size"), "saved size")


def dispatch(commands: list[str]) -> None:
    result = run_hyprctl("--batch", " ; ".join(f"dispatch {cmd}" for cmd in commands))
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "dispatch failed")


def toggle_floating() -> None:
    window = active_window()
    address = window_address(window)
    if not address:
        return

    if bool(window.get("floating")):
        position, size = geometry(window)
        with locked_state() as state:
            state["windows"][address] = {
                "pid": int(window.get("pid", -1)),
                "initial_class": str(window.get("initialClass") or ""),
                "at": list(position),
                "size": list(size),
                "monitor": int(window.get("monitor", -1)),
                "saved_at": time.time(),
            }

        dispatch([f"settiled address:{address}"])
        return

    with locked_state() as state:
        entry = state["windows"].get(address)
        if identity_matches(entry, window):
            position, size = saved_geometry(entry)
        else:
            state["windows"].pop(address, None)
            work_area = monitor_work_area(window) if is_terminal(window) else None
            position, size = initial_float_geometry(window, work_area)

    x, y = position
    width, height = size
    dispatch(
        [
            f"setfloating address:{address}",
            f"resizewindowpixel exact {width} {height},address:{address}",
            f"movewindowpixel exact {x} {y},address:{address}",
        ]
    )


def self_test() -> None:
    terminal = {
        "class": "kitty",
        "initialClass": "kitty",
        "at": [0, 30],
        "size": [1920, 1050],
    }
    assert initial_float_geometry(terminal, (0, 34, 1920, 1046)) == (
        (48, 66),
        TERMINAL_SIZE,
    )
    assert initial_float_geometry(terminal, (1920, 34, 1920, 1046)) == (
        (1968, 66),
        TERMINAL_SIZE,
    )

    browser = {
        "class": "firefox",
        "initialClass": "firefox",
        "at": [960, 30],
        "size": [960, 1050],
    }
    assert initial_float_geometry(browser) == ((998, 72), (883, 966))

    entry = {"pid": 42, "initial_class": "kitty"}
    assert identity_matches(entry, {"pid": 42, "initialClass": "kitty"})
    assert not identity_matches(entry, {"pid": 43, "initialClass": "kitty"})
    print("toggle_floating self-test: OK")


def main() -> int:
    try:
        if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
            self_test()
        elif len(sys.argv) == 1:
            toggle_floating()
        else:
            print(f"usage: {Path(sys.argv[0]).name} [--self-test]", file=sys.stderr)
            return 2
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"toggle_floating: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
