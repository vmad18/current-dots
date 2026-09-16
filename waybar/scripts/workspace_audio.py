#!/usr/bin/env python3

import fcntl
import json
import os
import select
import signal
import socket
import subprocess
import sys
import threading
import time


MARKER = ""
RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
LOCK_PATH = os.path.join(RUNTIME_DIR, "waybar-workspace-audio.lock")
REFRESH_INTERVAL = 30.0

GENERIC_TITLES = {
    "audio",
    "audiostream",
    "firefox",
    "chromium",
    "google chrome",
    "spotify",
}


def run_json(command):
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=2.0,
    )
    return json.loads(result.stdout)


def process_ancestors(pid, cache):
    if pid in cache:
        return cache[pid]

    ancestors = set()
    current = pid

    for _ in range(32):
        try:
            with open(f"/proc/{current}/stat", "r", encoding="utf-8") as stat_file:
                stat = stat_file.read()
            parent = int(stat[stat.rfind(")") + 2 :].split()[1])
        except (OSError, ValueError, IndexError):
            break

        if parent <= 1 or parent in ancestors:
            break

        ancestors.add(parent)
        current = parent

    cache[pid] = ancestors
    return ancestors


def candidate_windows(stream_pid, clients, ancestor_cache):
    exact = [client for client in clients if client.get("pid") == stream_pid]
    if exact:
        return exact

    stream_ancestors = process_ancestors(stream_pid, ancestor_cache)
    related = []

    for client in clients:
        client_pid = client.get("pid")
        if not isinstance(client_pid, int):
            continue

        if client_pid in stream_ancestors or stream_pid in process_ancestors(client_pid, ancestor_cache):
            related.append(client)

    return related


def normalized_title(value):
    return " ".join(str(value or "").casefold().split())


def title_matches(stream_title, client_title):
    stream_title = normalized_title(stream_title)
    client_title = normalized_title(client_title)

    if len(stream_title) < 6 or stream_title in GENERIC_TITLES:
        return False

    return stream_title in client_title or client_title in stream_title


def stream_is_active(stream):
    if stream.get("corked", True) or stream.get("mute", False):
        return False

    channels = stream.get("volume", {}).values()
    return any(channel.get("value", 0) > 0 for channel in channels)


def playing_mpris_titles():
    try:
        result = subprocess.run(
            [
                "playerctl",
                "-a",
                "metadata",
                "--format",
                "{{playerName}}\t{{status}}\t{{title}}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    players = []
    for line in result.stdout.splitlines():
        fields = line.split("\t", 2)
        if len(fields) == 3 and fields[1].casefold() == "playing" and fields[2].strip():
            players.append({"application": fields[0], "title": fields[2]})
    return players


def audio_workspace_state():
    streams = run_json(["pactl", "-f", "json", "list", "sink-inputs"])
    clients = run_json(["hyprctl", "clients", "-j"])
    ancestor_cache = {}
    workspaces = set()
    details = []
    active_applications = set()

    for stream in streams:
        if not stream_is_active(stream):
            continue

        properties = stream.get("properties", {})
        application = properties.get("application.name", "Unknown")
        active_applications.add(normalized_title(application))
        try:
            stream_pid = int(properties.get("application.process.id"))
        except (TypeError, ValueError):
            continue

        candidates = candidate_windows(stream_pid, clients, ancestor_cache)
        candidate_workspaces = {
            client.get("workspace", {}).get("id")
            for client in candidates
            if isinstance(client.get("workspace", {}).get("id"), int)
            and client.get("workspace", {}).get("id") > 0
        }
        media_name = properties.get("media.name", "")
        matching = [
            client for client in candidates if title_matches(media_name, client.get("title", ""))
        ]
        matched_workspaces = {
            client.get("workspace", {}).get("id")
            for client in matching
            if isinstance(client.get("workspace", {}).get("id"), int)
            and client.get("workspace", {}).get("id") > 0
        }

        if matched_workspaces:
            selected = matched_workspaces
            reason = "title"
        elif len(candidate_workspaces) == 1:
            selected = candidate_workspaces
            reason = "process"
        else:
            selected = set()
            reason = "ambiguous" if candidate_workspaces else "unmapped"

        workspaces.update(selected)
        details.append(
            {
                "application": properties.get("application.name", "Unknown"),
                "title": media_name,
                "workspaces": sorted(selected),
                "candidates": sorted(candidate_workspaces),
                "reason": reason,
            }
        )

    for player in playing_mpris_titles():
        player_name = normalized_title(player["application"])
        if not any(
            player_name.startswith(application) or application.startswith(player_name)
            for application in active_applications
        ):
            continue

        matched_workspaces = {
            client.get("workspace", {}).get("id")
            for client in clients
            if title_matches(player["title"], client.get("title", ""))
            and isinstance(client.get("workspace", {}).get("id"), int)
            and client.get("workspace", {}).get("id") > 0
        }
        workspaces.update(matched_workspaces)
        details.append(
            {
                "application": player["application"],
                "title": player["title"],
                "workspaces": sorted(matched_workspaces),
                "candidates": sorted(matched_workspaces),
                "reason": "mpris-title" if matched_workspaces else "mpris-unmapped",
            }
        )

    return workspaces, details


def current_numeric_workspaces():
    workspaces = run_json(["hyprctl", "workspaces", "-j"])
    return {
        workspace["id"]: workspace.get("name", "")
        for workspace in workspaces
        if isinstance(workspace.get("id"), int) and workspace["id"] > 0
    }


def rename_workspace(workspace_id, name):
    subprocess.run(
        ["hyprctl", "dispatch", "renameworkspace", str(workspace_id), name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=1.0,
    )


def apply_markers(audio_workspaces):
    for workspace_id, current_name in current_numeric_workspaces().items():
        plain_name = str(workspace_id)
        marked_name = f"{plain_name}{MARKER}"

        if current_name not in (plain_name, marked_name):
            continue

        wanted_name = marked_name if workspace_id in audio_workspaces else plain_name
        if current_name != wanted_name:
            rename_workspace(workspace_id, wanted_name)


def hyprland_event_socket():
    instance = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not instance:
        return None
    return os.path.join(RUNTIME_DIR, "hypr", instance, ".socket2.sock")


def watch_pipewire(changed, stopped):
    while not stopped.is_set():
        process = None
        try:
            process = subprocess.Popen(
                ["pactl", "subscribe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            if process.stdout is None:
                raise OSError("pactl did not expose stdout")

            while not stopped.is_set():
                readable, _writable, _exceptional = select.select(
                    [process.stdout], [], [], 1.0
                )
                if not readable:
                    continue

                event = process.stdout.readline()
                if not event:
                    break
                if "sink-input" in event or "server" in event:
                    changed.set()
        except OSError:
            stopped.wait(1.0)
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()


def watch_hyprland(changed, stopped):
    relevant = (
        "activewindow>>",
        "activewindowv2>>",
        "openwindow>>",
        "closewindow>>",
        "movewindow>>",
        "movewindowv2>>",
        "createworkspace>>",
        "createworkspacev2>>",
        "destroyworkspace>>",
        "destroyworkspacev2>>",
    )

    while not stopped.is_set():
        socket_path = hyprland_event_socket()
        if not socket_path:
            stopped.wait(1.0)
            continue

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(1.0)
                client.connect(socket_path)
                buffer = ""

                while not stopped.is_set():
                    try:
                        chunk = client.recv(4096)
                    except TimeoutError:
                        continue
                    if not chunk:
                        break

                    buffer += chunk.decode("utf-8", errors="replace")
                    lines = buffer.split("\n")
                    buffer = lines.pop()
                    if any(line.startswith(relevant) for line in lines):
                        changed.set()
        except OSError:
            stopped.wait(1.0)


def claim_instance():
    lock_file = open(LOCK_PATH, "w", encoding="utf-8")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return None

    lock_file.write(f"{os.getpid()}\n")
    lock_file.flush()
    return lock_file


def debug_main():
    workspaces, details = audio_workspace_state()
    print(json.dumps({"audio_workspaces": sorted(workspaces), "streams": details}, indent=2))


def daemon_main():
    lock_file = claim_instance()
    if lock_file is None:
        return 0

    changed = threading.Event()
    stopped = threading.Event()

    def stop(_signum, _frame):
        stopped.set()
        changed.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    watchers = (
        threading.Thread(target=watch_pipewire, args=(changed, stopped), daemon=True),
        threading.Thread(target=watch_hyprland, args=(changed, stopped), daemon=True),
    )
    for watcher in watchers:
        watcher.start()

    changed.set()

    try:
        while not stopped.is_set():
            changed.wait(REFRESH_INTERVAL)
            changed.clear()
            if stopped.wait(0.08):
                break

            try:
                workspaces, _details = audio_workspace_state()
                apply_markers(workspaces)
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
                stopped.wait(0.5)
    finally:
        stopped.set()
        try:
            apply_markers(set())
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            pass
        for watcher in watchers:
            watcher.join(timeout=1.5)
        lock_file.close()

    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        debug_main()
        raise SystemExit(0)

    raise SystemExit(daemon_main())
