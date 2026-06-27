#!/usr/bin/env python3

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from datetime import datetime, timedelta
from pathlib import Path


CACHE_SECONDS = 600
LOCATION = os.environ.get("WAYBAR_WEATHER_LOCATION", "").strip()


def cache_path():
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "waybar-clock-weather.json"


def weather_url():
    if LOCATION:
        place = urllib.parse.quote(LOCATION)
        return f"https://wttr.in/{place}?format=j1"

    return "https://wttr.in/?format=j1"


def load_cached():
    path = cache_path()
    try:
        if time.time() - path.stat().st_mtime <= CACHE_SECONDS:
            return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    return None


def save_cached(data):
    path = cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def fetch_weather():
    cached = load_cached()
    if cached is not None:
        return cached

    request = urllib.request.Request(
        weather_url(),
        headers={"User-Agent": "waybar-clock-weather/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            save_cached(data)
            return data
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        try:
            return json.loads(cache_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None


def icon_for(code, desc):
    code = str(code)
    desc = desc.lower()

    if code == "113":
        return "󰖙"
    if code == "116":
        return "󰖕"
    if code in {"119", "122"}:
        return "󰖐"
    if code in {"143", "248", "260"}:
        return "󰖑"
    if code in {"176", "263", "266", "293", "296", "299", "302", "305", "308", "353", "356", "359"} or "rain" in desc:
        return "󰖗"
    if code in {"179", "182", "185", "227", "230", "317", "320", "323", "326", "329", "332", "335", "338", "368", "371"} or "snow" in desc:
        return "󰖘"
    if code in {"200", "386", "389", "392", "395"} or "thunder" in desc:
        return "󰖓"

    return "󰖐"


def parse_hourly_slots(data, now):
    slots = []

    for day in data.get("weather", []):
        try:
            day_start = datetime.strptime(day["date"], "%Y-%m-%d")
        except (KeyError, ValueError):
            continue

        for hour in day.get("hourly", []):
            raw_time = str(hour.get("time", "0")).zfill(4)

            try:
                slot_time = day_start.replace(
                    hour=int(raw_time[:2]),
                    minute=int(raw_time[2:]),
                )
                temp = int(hour["tempF"])
            except (TypeError, ValueError, KeyError):
                continue

            desc = hour.get("weatherDesc", [{}])[0].get("value", "")
            code = hour.get("weatherCode", "")
            slots.append(
                {
                    "time": slot_time,
                    "temp": temp,
                    "desc": desc,
                    "icon": icon_for(code, desc),
                }
            )

    slots.sort(key=lambda slot: slot["time"])
    return [slot for slot in slots if slot["time"] >= now - timedelta(minutes=20)]


def hourly_chart(data):
    if not data:
        return []

    now = datetime.now()
    slots = [
        slot
        for slot in parse_hourly_slots(data, now)
        if slot["time"] <= now + timedelta(hours=6, minutes=20)
    ]

    if len(slots) < 2:
        slots = parse_hourly_slots(data, now)[:3]
    else:
        slots = slots[:3]

    if not slots:
        return []

    lines = ["", "Next 6h:"]

    for slot in slots:
        label = slot["time"].strftime("%-I%p").lower()
        lines.append(f"{label:>4}  {slot['icon']} {slot['temp']:>2}°F")

    return lines


def summarize_weather(data):
    if not data:
        return "Weather unavailable"

    current = data["current_condition"][0]
    desc = current["weatherDesc"][0]["value"]
    code = current.get("weatherCode", "")
    icon = icon_for(code, desc)

    area = data.get("nearest_area", [{}])[0]
    city = area.get("areaName", [{}])[0].get("value", "")
    region = area.get("region", [{}])[0].get("value", "")
    location = ", ".join(part for part in [city, region] if part)

    temp_f = current.get("temp_F", "?")
    feels_f = current.get("FeelsLikeF", "?")
    humidity = current.get("humidity", "?")
    wind_mph = current.get("windspeedMiles", "?")
    wind_dir = current.get("winddir16Point", "")

    lines = [
        f"{icon} {desc}",
        f"Temp: {temp_f}°F, feels {feels_f}°F",
        f"Humidity: {humidity}%",
        f"Wind: {wind_mph} mph {wind_dir}".rstrip(),
    ]

    if location:
        lines.insert(0, location)

    lines.extend(hourly_chart(data))

    return "\n".join(lines)


def main():
    now = datetime.now()
    text = now.strftime(" %I:%M %p - %b/%d").replace(" 0", " ")
    tooltip = summarize_weather(fetch_weather())
    print(json.dumps({"text": text, "tooltip": tooltip}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
