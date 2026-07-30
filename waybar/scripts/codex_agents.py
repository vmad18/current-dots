#!/usr/bin/env python3

from __future__ import annotations

import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from html import escape
from pathlib import Path


ICON = ""
SPINNER_CHARS = frozenset("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
STATE_REFRESH = 0.22
PROCESS_REFRESH = 2.0
CLIENT_REFRESH = 2.0
CLIENT_EVENT_THROTTLE = 0.30
TMUX_REFRESH = 0.45
TMUX_CLIENT_REFRESH = 2.0
TMUX_SEPARATOR = "\x1f"
THREAD_ID_PATTERN = re.compile(
    r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\.jsonl(?: \(deleted\))?$"
)

RUNTIME_ROOT = Path(
    os.environ.get(
        "WAYBAR_CODEX_RUNTIME_DIR",
        os.path.join(
            os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"),
            "waybar-codex-agents",
        ),
    )
)
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
SESSION_INDEX_PATH = CODEX_HOME / "session_index.jsonl"
SESSIONS_DIR = RUNTIME_ROOT / "sessions"
SNAPSHOT_PATH = RUNTIME_ROOT / "snapshot.json"
SEEN_PATH = RUNTIME_ROOT / "seen.json"
FALLBACK_PATH = RUNTIME_ROOT / "fallback.json"
STATE_LOCK_PATH = RUNTIME_ROOT / "state.lock"

COLOR_TEXT = "#cdd6f4"
COLOR_MUTED = "#7f849c"
COLOR_SUBTLE = "#555b70"
COLOR_ACCENT = "#9BD6FF"
COLOR_DONE = "#a9dcff"
COLOR_APPROVAL = "#f2c879"


def ensure_runtime() -> None:
    RUNTIME_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(RUNTIME_ROOT, 0o700)
        os.chmod(SESSIONS_DIR, 0o700)
    except OSError:
        pass


@contextmanager
def state_lock():
    ensure_runtime()
    with STATE_LOCK_PATH.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as source:
            return json.load(source)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return default


def atomic_write_json(path: Path, value) -> None:
    ensure_runtime()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}")
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write(encoded)
            target.write("\n")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def proc_stat(pid: int) -> tuple[int, int] | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = raw[raw.rfind(")") + 2 :].split()
        return int(fields[1]), int(fields[19])
    except (FileNotFoundError, PermissionError, OSError, ValueError, IndexError):
        return None


def proc_comm(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def proc_cwd(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return ""


def thread_id_from_rollout_path(path: str) -> str:
    match = THREAD_ID_PATTERN.search(path)
    return match.group(1) if match else ""


def proc_thread_id(pid: int) -> str:
    try:
        descriptors = list(Path(f"/proc/{pid}/fd").iterdir())
    except (FileNotFoundError, PermissionError, OSError):
        return ""

    for descriptor in descriptors:
        try:
            target = os.readlink(descriptor)
        except OSError:
            continue
        thread_id = thread_id_from_rollout_path(target)
        if thread_id:
            return thread_id
    return ""


def load_thread_names() -> dict[str, str]:
    names = {}
    try:
        with SESSION_INDEX_PATH.open("r", encoding="utf-8") as index:
            for line in index:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(record, dict):
                    continue
                thread_id = str(record.get("id") or "")
                thread_name = str(record.get("thread_name") or "").strip()
                if thread_id and thread_name:
                    names[thread_id] = thread_name
    except (FileNotFoundError, PermissionError, OSError):
        return {}
    return names


def walk_ancestors(pid: int, limit: int = 24) -> list[int]:
    ancestors = []
    seen = set()
    current = pid

    for _ in range(limit):
        if current <= 1 or current in seen:
            break
        ancestors.append(current)
        seen.add(current)
        stat = proc_stat(current)
        if not stat:
            break
        current = stat[0]

    return ancestors


def find_codex_ancestor(pid: int) -> tuple[int, int] | None:
    for ancestor in walk_ancestors(pid):
        if proc_comm(ancestor) != "codex":
            continue
        stat = proc_stat(ancestor)
        if stat:
            return ancestor, stat[1]
    return None


def discover_codex_processes() -> dict[int, dict]:
    processes = {}

    try:
        entries = list(Path("/proc").iterdir())
    except OSError:
        return processes

    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if proc_comm(pid) != "codex":
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
        except OSError:
            continue
        stat = proc_stat(pid)
        if not stat:
            continue
        processes[pid] = {
            "pid": pid,
            "ppid": stat[0],
            "start_ticks": stat[1],
            "cwd": proc_cwd(pid),
            "thread_id": proc_thread_id(pid),
        }

    return processes


def safe_key(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.")
    return cleaned[:96] or "session"


def hook_main() -> int:
    try:
        payload = json.load(sys.stdin)
        event = str(payload.get("hook_event_name") or "")
        session_id = str(payload.get("session_id") or "unknown")
        turn_id = str(payload.get("turn_id") or "")
        now = time.time()
        ancestor = find_codex_ancestor(os.getpid())

        if not ancestor or not event:
            print("{}")
            return 0

        codex_pid, start_ticks = ancestor
        record_key = f"{safe_key(session_id)}-{codex_pid}-{start_ticks}"
        record_path = SESSIONS_DIR / f"{record_key}.json"

        with state_lock():
            record = load_json(record_path, {})
            if not isinstance(record, dict):
                record = {}

            record.update(
                {
                    "version": 1,
                    "record_key": record_key,
                    "session_id": session_id,
                    "pid": codex_pid,
                    "start_ticks": start_ticks,
                    "cwd": str(payload.get("cwd") or record.get("cwd") or proc_cwd(codex_pid)),
                    "model": str(payload.get("model") or record.get("model") or ""),
                    "last_event": event,
                    "updated_at": now,
                }
            )
            record.setdefault("subagents", {})

            if event == "SessionStart":
                record.update(
                    {
                        "state": "idle",
                        "state_since": now,
                        "turn_id": "",
                        "started_at": None,
                        "finished_at": None,
                        "completion_key": "",
                        "attention_at": None,
                        "attention_key": "",
                        "subagents": {},
                    }
                )
            elif event == "UserPromptSubmit":
                record.update(
                    {
                        "state": "working",
                        "state_since": now,
                        "turn_id": turn_id,
                        "started_at": now,
                        "finished_at": None,
                        "completion_key": "",
                        "attention_at": None,
                        "attention_key": "",
                    }
                )
            elif event == "PermissionRequest":
                active_turn = turn_id or str(record.get("turn_id") or "unknown")
                record.update(
                    {
                        "state": "approval",
                        "state_since": now,
                        "turn_id": active_turn,
                        "attention_at": now,
                        "attention_key": f"{record_key}:approval:{active_turn}",
                        "approval_tool": str(payload.get("tool_name") or ""),
                    }
                )
            elif event == "Stop":
                active_turn = turn_id or str(record.get("turn_id") or f"at-{time.time_ns()}")
                record.update(
                    {
                        "state": "done",
                        "state_since": now,
                        "turn_id": active_turn,
                        "finished_at": now,
                        "completion_key": f"{record_key}:turn:{active_turn}",
                        "attention_at": None,
                        "attention_key": "",
                    }
                )
            elif event == "SubagentStart":
                agent_id = str(payload.get("agent_id") or "")
                if agent_id:
                    record["subagents"][agent_id] = {
                        "agent_type": str(payload.get("agent_type") or "agent"),
                        "started_at": now,
                    }
            elif event == "SubagentStop":
                agent_id = str(payload.get("agent_id") or "")
                if agent_id:
                    record["subagents"].pop(agent_id, None)

            atomic_write_json(record_path, record)
    except Exception as error:  # Hooks must never interfere with the Codex turn.
        print(f"waybar Codex hook: {error}", file=sys.stderr)

    print("{}")
    return 0


def hypr_socket_path(name: str) -> Path | None:
    instance = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not instance:
        return None

    candidates = []
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        candidates.append(Path(runtime_dir) / "hypr" / instance / name)
    candidates.append(Path("/tmp") / "hypr" / instance / name)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def hypr_request(command: str, timeout: float = 0.6) -> str:
    socket_path = hypr_socket_path(".socket.sock")
    if not socket_path:
        raise OSError("Hyprland command socket is unavailable")

    chunks = []
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(str(socket_path))
        client.sendall(command.encode("utf-8"))
        client.shutdown(socket.SHUT_WR)
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


def fetch_clients() -> list[dict]:
    try:
        response = hypr_request("j/clients")
        clients = json.loads(response)
        return clients if isinstance(clients, list) else []
    except (OSError, json.JSONDecodeError, socket.timeout):
        try:
            result = subprocess.run(
                ["hyprctl", "clients", "-j"],
                check=True,
                capture_output=True,
                text=True,
                timeout=0.8,
            )
            clients = json.loads(result.stdout)
            return clients if isinstance(clients, list) else []
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return []


def fetch_tmux_panes() -> list[dict]:
    fields = (
        "#{session_name}",
        "#{session_id}",
        "#{window_index}",
        "#{window_name}",
        "#{window_id}",
        "#{pane_index}",
        "#{pane_id}",
        "#{pane_pid}",
        "#{pane_title}",
        "#{pane_current_command}",
        "#{pane_current_path}",
        "#{pane_active}",
        "#{window_active}",
        "#{session_attached}",
    )
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", TMUX_SEPARATOR.join(fields)],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.8,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0:
        return []

    panes = []
    for line in result.stdout.splitlines():
        values = line.split(TMUX_SEPARATOR)
        if len(values) != len(fields):
            continue
        try:
            pane_pid = int(values[7])
            window_index = int(values[2])
            pane_index = int(values[5])
        except ValueError:
            continue

        raw_title = values[8]
        panes.append(
            {
                "session_name": values[0],
                "session_id": values[1],
                "window_index": window_index,
                "window_name": values[3],
                "window_id": values[4],
                "pane_index": pane_index,
                "pane_id": values[6],
                "pane_pid": pane_pid,
                "title": clean_terminal_title(raw_title),
                "state": title_state(raw_title),
                "current_command": values[9],
                "current_path": values[10],
                "pane_active": values[11] == "1",
                "window_active": values[12] == "1",
                "session_attached": int(values[13] or 0),
            }
        )
    return panes


def fetch_tmux_clients() -> list[dict]:
    fields = (
        "#{client_name}",
        "#{client_pid}",
        "#{client_tty}",
        "#{session_name}",
        "#{session_id}",
        "#{client_flags}",
    )
    try:
        result = subprocess.run(
            ["tmux", "list-clients", "-F", TMUX_SEPARATOR.join(fields)],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.8,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0:
        return []

    clients = []
    for line in result.stdout.splitlines():
        values = line.split(TMUX_SEPARATOR)
        if len(values) != len(fields):
            continue
        try:
            client_pid = int(values[1])
        except ValueError:
            continue
        clients.append(
            {
                "client_name": values[0],
                "client_pid": client_pid,
                "client_tty": values[2],
                "session_name": values[3],
                "session_id": values[4],
                "client_flags": values[5].split(","),
            }
        )
    return clients


def tmux_command(*arguments: str) -> bool:
    try:
        result = subprocess.run(
            ["tmux", *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.8,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def dispatch(dispatcher: str, argument: str) -> bool:
    try:
        response = hypr_request(f"dispatch {dispatcher} {argument}")
        if response.strip().lower().startswith("ok"):
            return True
    except (OSError, socket.timeout):
        pass

    try:
        result = subprocess.run(
            ["hyprctl", "dispatch", dispatcher, argument],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.8,
        )
        return result.returncode == 0 and "ok" in result.stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return False


class HyprlandEvents:
    def __init__(self) -> None:
        self.dirty = threading.Event()
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _watch(self) -> None:
        relevant = (
            "activewindow>>",
            "activewindowv2>>",
            "workspace>>",
            "workspacev2>>",
            "movewindow>>",
            "movewindowv2>>",
            "openwindow>>",
            "closewindow>>",
            "windowtitle>>",
            "windowtitlev2>>",
        )

        while True:
            socket_path = hypr_socket_path(".socket2.sock")
            if not socket_path:
                time.sleep(1.0)
                continue

            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(str(socket_path))
                    stream = client.makefile("r", encoding="utf-8", errors="replace")
                    for event in stream:
                        if event.startswith(relevant):
                            self.dirty.set()
            except OSError:
                time.sleep(0.5)


def load_hook_records() -> dict[tuple[int, int], dict]:
    records = {}
    try:
        paths = list(SESSIONS_DIR.glob("*.json"))
    except OSError:
        return records

    for path in paths:
        record = load_json(path, {})
        if not isinstance(record, dict):
            continue
        try:
            key = (int(record["pid"]), int(record["start_ticks"]))
        except (KeyError, TypeError, ValueError):
            continue
        previous = records.get(key)
        if not previous or float(record.get("updated_at") or 0) >= float(previous.get("updated_at") or 0):
            records[key] = record

    return records


def title_state(title: str) -> str:
    lowered = title.casefold()
    if "approval required" in lowered or "permission required" in lowered:
        return "approval"
    if "action required" in lowered:
        return "done"
    stripped = title.lstrip("[ .]│ ")
    if stripped and stripped[0] in SPINNER_CHARS:
        return "working"
    return "idle"


def clean_terminal_title(title: str) -> str:
    stripped = title.lstrip("[ .]│ ")
    if stripped and stripped[0] in SPINNER_CHARS:
        stripped = stripped[1:].lstrip()
    return stripped or title.strip()


def process_key(process: dict) -> str:
    return f"{process['pid']}:{process['start_ticks']}"


def update_fallback(fallback: dict, process: dict, derived_state: str, now: float) -> tuple[dict, bool]:
    processes = fallback.setdefault("processes", {})
    key = process_key(process)
    previous = processes.get(key, {})
    previous_state = str(previous.get("state") or "")
    effective_state = derived_state
    changed = False
    generation = int(previous.get("generation") or 0)
    attention_generation = int(previous.get("attention_generation") or 0)
    started_at = previous.get("started_at")
    finished_at = previous.get("finished_at")
    attention_at = previous.get("attention_at")

    # Codex briefly advertises completion in the terminal title, then restores
    # the normal title. Keep unseen terminal-derived states until a new turn.
    if derived_state == "idle" and previous_state in {"done", "approval"}:
        effective_state = previous_state

    if derived_state == "working" and (previous_state != "working" or not started_at):
        started_at = now
        changed = True
    if derived_state == "done" and previous_state != "done":
        generation += 1
        finished_at = now
        changed = True
    elif derived_state == "approval" and previous_state != "approval":
        attention_generation += 1
        attention_at = now
        changed = True

    current = {
        "state": effective_state,
        "generation": generation,
        "attention_generation": attention_generation,
        "started_at": started_at,
        "finished_at": finished_at,
        "attention_at": attention_at,
        "updated_at": now,
    }
    if any(
        previous.get(field) != current.get(field)
        for field in (
            "state",
            "generation",
            "attention_generation",
            "started_at",
            "finished_at",
            "attention_at",
        )
    ):
        changed = True
    processes[key] = current
    return current, changed


def window_for_pid(pid: int, clients: list[dict]) -> dict | None:
    by_pid = {}
    for client in clients:
        try:
            by_pid.setdefault(int(client.get("pid")), []).append(client)
        except (TypeError, ValueError):
            continue

    for ancestor in walk_ancestors(pid):
        matches = by_pid.get(ancestor)
        if not matches:
            continue
        return min(matches, key=lambda item: int(item.get("focusHistoryID", 9999)))
    return None


def window_for_process(process: dict, clients: list[dict]) -> dict | None:
    return window_for_pid(int(process["pid"]), clients)


def tmux_pane_for_process(process: dict, panes: list[dict]) -> dict | None:
    ancestor_order = {
        ancestor: index for index, ancestor in enumerate(walk_ancestors(int(process["pid"])))
    }
    matches = [pane for pane in panes if int(pane.get("pane_pid") or 0) in ancestor_order]
    if not matches:
        return None
    return min(matches, key=lambda pane: ancestor_order[int(pane["pane_pid"])])


def tmux_client_for_pane(pane: dict, clients: list[dict]) -> dict | None:
    session_id = str(pane.get("session_id") or "")
    session_name = str(pane.get("session_name") or "")
    matches = [
        client
        for client in clients
        if (session_id and client.get("session_id") == session_id)
        or (session_name and client.get("session_name") == session_name)
    ]
    if not matches:
        return None
    return min(
        matches,
        key=lambda client: (
            "focused" not in client.get("client_flags", []),
            int(client.get("client_pid") or 0),
        ),
    )


def project_name(cwd: str) -> str:
    cleaned = cwd.rstrip("/")
    if not cleaned:
        return "Codex"
    return os.path.basename(cleaned) or cleaned


def build_agents(
    processes: dict[int, dict],
    clients: list[dict],
    tmux_panes: list[dict],
    tmux_clients: list[dict],
    thread_names: dict[str, str],
    records: dict[tuple[int, int], dict],
    fallback: dict,
    now: float,
) -> tuple[list[dict], bool]:
    agents = []
    fallback_changed = False
    live_keys = set()

    for process in processes.values():
        proc_key = process_key(process)
        process_thread_id = str(process.get("thread_id") or "")
        live_keys.add(proc_key)
        tmux_pane = tmux_pane_for_process(process, tmux_panes)
        tmux_client = tmux_client_for_pane(tmux_pane, tmux_clients) if tmux_pane else None
        if tmux_client:
            window = window_for_pid(int(tmux_client["client_pid"]), clients)
        elif tmux_pane:
            window = None
        else:
            window = window_for_process(process, clients)

        if tmux_pane:
            title = str(tmux_pane.get("title") or "")
            derived = str(tmux_pane.get("state") or "idle")
        else:
            title = str((window or {}).get("title") or "")
            derived = title_state(title)
        fallback_record, changed = update_fallback(fallback, process, derived, now)
        fallback_changed = fallback_changed or changed
        record = records.get((int(process["pid"]), int(process["start_ticks"])))

        if record:
            state = str(record.get("state") or "idle")
            if derived == "working":
                state = "working"
            elif derived in ("done", "approval") and state == "working":
                state = derived
            cwd = str(record.get("cwd") or process.get("cwd") or "")
            model = str(record.get("model") or "")
            started_at = record.get("started_at")
            finished_at = record.get("finished_at")
            attention_at = record.get("attention_at")
            completion_key = str(record.get("completion_key") or "")
            attention_key = str(record.get("attention_key") or "")
            subagents = len(record.get("subagents") or {})
            session_id = str(record.get("session_id") or process_thread_id)
        else:
            state = str(fallback_record.get("state") or "idle")
            cwd = str(process.get("cwd") or "")
            model = ""
            started_at = fallback_record.get("started_at") if state == "working" else None
            finished_at = fallback_record.get("finished_at")
            attention_at = fallback_record.get("attention_at")
            generation = int(fallback_record.get("generation") or 0)
            completion_key = f"fallback:{proc_key}:done:{generation}" if state == "done" else ""
            attention_generation = int(fallback_record.get("attention_generation") or 0)
            attention_key = (
                f"fallback:{proc_key}:approval:{attention_generation}" if state == "approval" else ""
            )
            subagents = 0
            session_id = process_thread_id

        if session_id not in thread_names and process_thread_id:
            session_id = process_thread_id

        if state == "done" and not completion_key:
            generation = int(fallback_record.get("generation") or 0)
            completion_key = f"fallback:{proc_key}:done:{generation}"
            finished_at = finished_at or fallback_record.get("finished_at") or now
        if state == "approval" and not attention_key:
            attention_generation = int(fallback_record.get("attention_generation") or 0)
            attention_key = f"fallback:{proc_key}:approval:{attention_generation}"
            attention_at = attention_at or fallback_record.get("attention_at") or now

        workspace = (window or {}).get("workspace") or {}
        workspace_name = str(workspace.get("name") or workspace.get("id") or "")
        address = str((window or {}).get("address") or "")
        window_focused = int((window or {}).get("focusHistoryID", -1)) == 0
        if tmux_pane:
            focused = (
                window_focused
                and bool(tmux_pane.get("window_active"))
                and bool(tmux_pane.get("pane_active"))
            )
        else:
            focused = window_focused
        project = project_name(cwd)
        thread_name = str(thread_names.get(session_id) or "")

        agents.append(
            {
                "key": proc_key,
                "pid": int(process["pid"]),
                "start_ticks": int(process["start_ticks"]),
                "session_id": session_id,
                "name": thread_name or project,
                "thread_name": thread_name,
                "project": project,
                "cwd": cwd,
                "model": model,
                "state": state,
                "started_at": started_at,
                "finished_at": finished_at,
                "attention_at": attention_at,
                "completion_key": completion_key,
                "attention_key": attention_key,
                "subagents": subagents,
                "workspace": workspace_name,
                "window_address": address,
                "window_pid": int((window or {}).get("pid") or 0),
                "focused": focused,
                "title": title,
                "tmux_session": str((tmux_pane or {}).get("session_name") or ""),
                "tmux_session_id": str((tmux_pane or {}).get("session_id") or ""),
                "tmux_window_index": (tmux_pane or {}).get("window_index"),
                "tmux_window_name": str((tmux_pane or {}).get("window_name") or ""),
                "tmux_window_id": str((tmux_pane or {}).get("window_id") or ""),
                "tmux_pane_index": (tmux_pane or {}).get("pane_index"),
                "tmux_pane_id": str((tmux_pane or {}).get("pane_id") or ""),
                "tmux_client_name": str((tmux_client or {}).get("client_name") or ""),
                "tmux_attached": bool(tmux_client),
            }
        )

    fallback_processes = fallback.setdefault("processes", {})
    for stale_key in list(fallback_processes):
        if stale_key not in live_keys:
            fallback_processes.pop(stale_key, None)
            fallback_changed = True

    agents.sort(key=agent_sort_key)
    return agents, fallback_changed


def workspace_sort_key(workspace: str):
    try:
        return 0, int(workspace)
    except (TypeError, ValueError):
        return 1, str(workspace)


def agent_sort_key(agent: dict):
    workspace = workspace_sort_key(agent.get("workspace", ""))
    if agent.get("tmux_pane_id"):
        return (
            *workspace,
            0,
            str(agent.get("tmux_session") or ""),
            int(agent.get("tmux_window_index") or 0),
            int(agent.get("tmux_pane_index") or 0),
            int(agent.get("pid") or 0),
        )
    return (*workspace, 1, "", 0, 0, int(agent.get("pid") or 0))


def seen_items() -> dict[str, float]:
    data = load_json(SEEN_PATH, {})
    items = data.get("items", {}) if isinstance(data, dict) else {}
    return items if isinstance(items, dict) else {}


def unseen_done(agents: list[dict], seen: dict[str, float]) -> list[dict]:
    return sorted(
        [
            agent
            for agent in agents
            if agent.get("state") == "done"
            and agent.get("completion_key")
            and agent["completion_key"] not in seen
        ],
        key=lambda agent: float(agent.get("finished_at") or 0),
    )


def unseen_approvals(agents: list[dict], seen: dict[str, float]) -> list[dict]:
    return sorted(
        [
            agent
            for agent in agents
            if agent.get("state") == "approval"
            and agent.get("attention_key")
            and agent["attention_key"] not in seen
        ],
        key=lambda agent: float(agent.get("attention_at") or 0),
    )


def module_text(agents: list[dict], seen: dict[str, float]) -> tuple[str, list[str]]:
    total = len(agents)
    done = unseen_done(agents, seen)
    approvals = unseen_approvals(agents, seen)
    working = [agent for agent in agents if agent.get("state") == "working"]

    icon = f'<span foreground="{COLOR_TEXT}">{ICON}</span>'
    count = f'<span foreground="{COLOR_MUTED}">{total}</span>'
    parts = [icon, count]
    classes = []

    if not agents:
        parts.append(f'<span foreground="{COLOR_SUBTLE}">·</span>')
        classes.append("none")
    elif working:
        classes.append("working")
    elif done:
        classes.append("done")
    elif approvals:
        classes.append("attention")
    else:
        parts.append(f'<span foreground="{COLOR_MUTED}">○</span>')
        classes.append("idle")

    if done:
        parts.append(f'<span foreground="{COLOR_DONE}">✓{len(done)}</span>')
        classes.append("has-done")
    if approvals:
        parts.append(f'<span foreground="{COLOR_APPROVAL}">!{len(approvals)}</span>')
        classes.append("has-approval")

    return " ".join(parts), classes


def short_age(timestamp, now: float, suffix: bool = False) -> str:
    if not timestamp:
        return "now"
    seconds = max(0, int(now - float(timestamp)))
    if seconds < 60:
        value = "<1m"
    elif seconds < 3600:
        value = f"{seconds // 60}m"
    elif seconds < 86400:
        value = f"{seconds // 3600}h"
    else:
        value = f"{seconds // 86400}d"
    return f"{value} ago" if suffix else value


def truncate(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def tooltip_markup(agents: list[dict], seen: dict[str, float], now: float) -> str:
    total = len(agents)
    done = unseen_done(agents, seen)
    approvals = unseen_approvals(agents, seen)
    working = [agent for agent in agents if agent.get("state") == "working"]
    tmux_agents = [agent for agent in agents if agent.get("tmux_pane_id")]

    summary = [f"{total} live"]
    if working:
        summary.append(f"{len(working)} working")
    if tmux_agents:
        summary.append(f"{len(tmux_agents)} in tmux")
    if done:
        summary.append(f"{len(done)} ready")
    if approvals:
        summary.append(f"{len(approvals)} approval")

    lines = [
        f'<span weight="bold" foreground="{COLOR_TEXT}">CODEX</span>  '
        f'<span foreground="{COLOR_MUTED}">{escape(" · ".join(summary))}</span>'
    ]

    if not agents:
        lines.extend(["", f'<span foreground="{COLOR_MUTED}">No live agents</span>'])
        return "\n".join(lines)

    next_key = done[0].get("completion_key") if done else ""

    def tooltip_order(agent: dict):
        completion_key = agent.get("completion_key")
        attention_key = agent.get("attention_key")
        if completion_key and completion_key not in seen and agent.get("state") == "done":
            return 0, float(agent.get("finished_at") or 0)
        if attention_key and attention_key not in seen and agent.get("state") == "approval":
            return 1, float(agent.get("attention_at") or 0)
        if agent.get("state") == "working":
            return 2, float(agent.get("started_at") or 0)
        if agent.get("state") == "idle":
            return 3, agent_sort_key(agent)
        return 4, agent_sort_key(agent)

    for agent in sorted(agents, key=tooltip_order):
        state = agent.get("state")
        is_seen = bool(agent.get("completion_key") and agent["completion_key"] in seen)
        if state == "working":
            symbol, color = "●", COLOR_ACCENT
            detail = f"working · {short_age(agent.get('started_at'), now)}"
        elif state == "approval":
            symbol, color = "!", COLOR_APPROVAL
            detail = f"approval · {short_age(agent.get('attention_at'), now, suffix=True)}"
        elif state == "done":
            symbol, color = "✓", COLOR_MUTED if is_seen else COLOR_DONE
            label = "seen" if is_seen else "complete"
            detail = f"{label} · {short_age(agent.get('finished_at'), now, suffix=True)}"
        else:
            symbol, color = "○", COLOR_MUTED
            detail = "idle"

        if agent.get("model"):
            detail += f" · {agent['model']}"
        if int(agent.get("subagents") or 0):
            detail += f" · {agent['subagents']} subagents"
        if agent.get("tmux_pane_id") and not agent.get("tmux_attached"):
            detail += " · detached"

        name = truncate(str(agent.get("name") or "Codex"), 28)
        workspace = str(agent.get("workspace") or "")
        pane_label = ""
        if agent.get("tmux_pane_id"):
            session = str(agent.get("tmux_session") or "?")
            window_index = agent.get("tmux_window_index")
            pane_index = agent.get("tmux_pane_index")
            if pane_index is not None:
                pane_label = f'  <span foreground="{COLOR_MUTED}">{pane_index}</span>'
            location = f"tmux {session}:{window_index}"
            if workspace:
                location += f" · ws {workspace}"
        else:
            location = f"ws {workspace or 'background'}"
        detail += f" · {location}"
        marker = ""
        if next_key and agent.get("completion_key") == next_key:
            marker = f'  <span weight="bold" foreground="{COLOR_ACCENT}">NEXT</span>'
        elif agent.get("focused"):
            marker = f'  <span foreground="{COLOR_MUTED}">HERE</span>'

        lines.extend(
            [
                "",
                f'<span foreground="{color}">{symbol}</span>  '
                f'<span weight="bold" foreground="{COLOR_TEXT}">{escape(name)}</span>'
                f"{pane_label}{marker}",
                f'<span foreground="{COLOR_MUTED}">   {escape(detail)}</span>',
            ]
        )

    return "\n".join(lines)


def waybar_payload(agents: list[dict], seen: dict[str, float], now: float) -> dict:
    text, classes = module_text(agents, seen)
    return {
        "text": text,
        "tooltip": tooltip_markup(agents, seen, now),
        "class": classes,
    }


def watch_main() -> int:
    ensure_runtime()
    events = HyprlandEvents()
    events.start()

    processes = {}
    clients = []
    tmux_panes = []
    tmux_clients = []
    thread_names = {}
    records = {}
    fallback = load_json(FALLBACK_PATH, {"version": 1, "processes": {}})
    if not isinstance(fallback, dict):
        fallback = {"version": 1, "processes": {}}
    agents = []
    seen = seen_items()
    last_output = ""
    last_snapshot = ""
    next_process_refresh = 0.0
    next_state_refresh = 0.0
    next_client_refresh = 0.0
    next_tmux_refresh = 0.0
    next_tmux_client_refresh = 0.0
    last_client_refresh = 0.0

    while True:
        now = time.time()
        rebuild = False

        if now >= next_process_refresh:
            discovered = discover_codex_processes()
            refreshed_thread_names = load_thread_names()
            if canonical_json(discovered) != canonical_json(processes):
                processes = discovered
                rebuild = True
                events.dirty.set()
            if canonical_json(refreshed_thread_names) != canonical_json(thread_names):
                thread_names = refreshed_thread_names
                rebuild = True
            next_process_refresh = now + PROCESS_REFRESH

        event_refresh = events.dirty.is_set() and now - last_client_refresh >= CLIENT_EVENT_THROTTLE
        if event_refresh or now >= next_client_refresh:
            refreshed_clients = fetch_clients()
            if canonical_json(refreshed_clients) != canonical_json(clients):
                clients = refreshed_clients
                rebuild = True
            events.dirty.clear()
            last_client_refresh = now
            next_client_refresh = now + CLIENT_REFRESH

        if now >= next_tmux_refresh:
            refreshed_tmux_panes = fetch_tmux_panes()
            if canonical_json(refreshed_tmux_panes) != canonical_json(tmux_panes):
                tmux_panes = refreshed_tmux_panes
                rebuild = True
            next_tmux_refresh = now + (TMUX_REFRESH if refreshed_tmux_panes else PROCESS_REFRESH)

        if now >= next_tmux_client_refresh:
            refreshed_tmux_clients = fetch_tmux_clients()
            if canonical_json(refreshed_tmux_clients) != canonical_json(tmux_clients):
                tmux_clients = refreshed_tmux_clients
                rebuild = True
            next_tmux_client_refresh = now + TMUX_CLIENT_REFRESH

        if now >= next_state_refresh:
            refreshed_records = load_hook_records()
            refreshed_seen = seen_items()
            if canonical_json(refreshed_records) != canonical_json(records):
                records = refreshed_records
                rebuild = True
            if canonical_json(refreshed_seen) != canonical_json(seen):
                seen = refreshed_seen
                rebuild = True
            next_state_refresh = now + STATE_REFRESH

        if rebuild or not agents and processes:
            agents, fallback_changed = build_agents(
                processes,
                clients,
                tmux_panes,
                tmux_clients,
                thread_names,
                records,
                fallback,
                now,
            )
            if fallback_changed:
                atomic_write_json(FALLBACK_PATH, fallback)

            snapshot = {"version": 1, "updated_at": now, "agents": agents}
            snapshot_key = canonical_json({"agents": agents})
            if snapshot_key != last_snapshot:
                atomic_write_json(SNAPSHOT_PATH, snapshot)
                last_snapshot = snapshot_key

        payload = waybar_payload(agents, seen, now)
        output = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if output != last_output:
            print(output, flush=True)
            last_output = output

        time.sleep(STATE_REFRESH)


def mark_seen(key: str) -> None:
    if not key:
        return
    with state_lock():
        data = load_json(SEEN_PATH, {"version": 1, "items": {}})
        if not isinstance(data, dict):
            data = {"version": 1, "items": {}}
        items = data.setdefault("items", {})
        if not isinstance(items, dict):
            items = {}
            data["items"] = items
        cutoff = time.time() - 7 * 86400
        data["items"] = {item: stamp for item, stamp in items.items() if float(stamp or 0) >= cutoff}
        data["items"][key] = time.time()
        atomic_write_json(SEEN_PATH, data)


def focus_agent(agent: dict) -> bool:
    address = str(agent.get("window_address") or "")
    workspace = str(agent.get("workspace") or "")
    window_pid = int(agent.get("window_pid") or 0)
    tmux_pane_id = str(agent.get("tmux_pane_id") or "")

    if not address and not window_pid:
        return False
    if workspace:
        dispatch("workspace", workspace)

    window_focused = False
    if address:
        window_focused = dispatch("focuswindow", f"address:{address}")
    if not window_focused and window_pid:
        window_focused = dispatch("focuswindow", f"pid:{window_pid}")
    if not window_focused:
        return False

    if not tmux_pane_id:
        return True

    client_name = str(agent.get("tmux_client_name") or "")
    session_id = str(agent.get("tmux_session_id") or "")
    window_id = str(agent.get("tmux_window_id") or "")
    if client_name and session_id:
        tmux_command("switch-client", "-c", client_name, "-t", session_id)
    if window_id and not tmux_command("select-window", "-t", window_id):
        return False
    return tmux_command("select-pane", "-t", tmux_pane_id)


def cycle_target(agents: list[dict]) -> dict | None:
    focusable = sorted(
        [agent for agent in agents if agent.get("window_address") or agent.get("window_pid")],
        key=agent_sort_key,
    )
    if not focusable:
        return None
    for index, agent in enumerate(focusable):
        if agent.get("focused"):
            return focusable[(index + 1) % len(focusable)]
    return focusable[0]


def focus_main(always_cycle: bool = False) -> int:
    snapshot = load_json(SNAPSHOT_PATH, {})
    agents = snapshot.get("agents", []) if isinstance(snapshot, dict) else []
    if not isinstance(agents, list) or not agents:
        return 0

    seen = seen_items()
    target = None
    seen_key = ""

    if not always_cycle:
        done = unseen_done(agents, seen)
        approvals = unseen_approvals(agents, seen)
        candidates = done if done else approvals
        for candidate in candidates:
            if candidate.get("window_address") or candidate.get("window_pid"):
                target = candidate
                seen_key = str(candidate.get("completion_key") or candidate.get("attention_key") or "")
                break

    if target is None:
        target = cycle_target(agents)
    if target and focus_agent(target) and seen_key:
        mark_seen(seen_key)
    return 0


def debug_main() -> int:
    snapshot = load_json(SNAPSHOT_PATH, {"agents": []})
    seen = seen_items()
    print(json.dumps({"snapshot": snapshot, "seen": seen}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "watch"
    if mode == "hook":
        return hook_main()
    if mode == "focus-next":
        return focus_main(always_cycle=False)
    if mode == "focus-cycle":
        return focus_main(always_cycle=True)
    if mode == "debug":
        return debug_main()
    if mode == "watch":
        return watch_main()
    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
