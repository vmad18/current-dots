#!/usr/bin/env python3
"""Report the active firmware power mode to Waybar."""

import json
from pathlib import Path

try:
    mode = Path('/sys/firmware/acpi/platform_profile').read_text().strip()
except OSError:
    mode = 'unknown'

labels = {
    'low-power': 'Low power',
    'balanced': 'Balanced',
    'performance': 'Performance',
}
if mode not in labels:
    mode = 'unknown'

print(json.dumps({
    'text': '',
    'class': mode,
    'tooltip': 'Power mode: ' + labels.get(mode, 'Unavailable'),
}))
