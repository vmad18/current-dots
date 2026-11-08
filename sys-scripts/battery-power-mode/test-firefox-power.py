#!/usr/bin/env python3
"""Compare battery draw in an existing Firefox test scope; restore quota on exit."""
import csv
import json
import signal
import subprocess
import time
from pathlib import Path

UNIT = 'firefox-power-test.scope'
BATTERY = Path('/sys/class/power_supply/BAT0')
OUTPUT = Path.home() / '.local/share/battery-power-mode' / time.strftime('firefox-test-%Y%m%d-%H%M%S.csv')

def ctl(*args):
    return subprocess.check_output(['systemctl', '--user', *args], text=True).strip()

def read(name):
    return (BATTERY / name).read_text().strip()

def interrupted(signum, frame):
    raise KeyboardInterrupt

def main():
    group = Path('/sys/fs/cgroup' + ctl('show', UNIT, '-p', 'ControlGroup', '--value'))
    if ctl('show', UNIT, '-p', 'CPUQuotaPerSecUSec', '--value') != 'infinity':
        raise SystemExit('Expected an initially uncapped test scope')
    profile = Path('/sys/firmware/acpi/platform_profile').read_text().strip()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    print(f'Results: {OUTPUT}', flush=True)
    try:
        with OUTPUT.open('w') as f:
            writer = csv.DictWriter(f, fieldnames=['phase', 'quota', 'elapsed_s', 'power_w', 'energy_wh', 'cpu_usage_usec', 'throttled_usec', 'nr_throttled'])
            writer.writeheader()
            # ABBA reduces bias from a gradual change in workload or temperature.
            for phase, quota in [('A1', 'infinity'), ('B1', '25%'), ('B2', '25%'), ('A2', 'infinity')]:
                ctl('set-property', '--runtime', UNIT, 'CPUQuota=' + ('' if quota == 'infinity' else quota))
                print(f'{phase}: CPUQuota={quota}; settling 10s, measuring 45s', flush=True)
                time.sleep(10)
                start = time.monotonic()
                rows = []
                for i in range(10):
                    if read('status') != 'Discharging' or int(read('capacity')) <= 5:
                        raise RuntimeError('Stopped: battery charging, not discharging, or at/below 5%')
                    if Path('/sys/firmware/acpi/platform_profile').read_text().strip() != profile:
                        raise RuntimeError('Stopped: firmware power mode changed')
                    stats = dict(line.split() for line in (group / 'cpu.stat').read_text().splitlines())
                    row = dict(phase=phase, quota=quota, elapsed_s=round(time.monotonic()-start, 3), power_w=int(read('power_now'))/1e6, energy_wh=int(read('energy_now'))/1e6, cpu_usage_usec=int(stats['usage_usec']), throttled_usec=int(stats.get('throttled_usec', 0)), nr_throttled=int(stats.get('nr_throttled', 0)))
                    writer.writerow(row)
                    f.flush()
                    rows.append(row)
                    if i < 9:
                        time.sleep(5)
                first, last = rows[0], rows[-1]
                seconds = last['elapsed_s'] - first['elapsed_s']
                print(json.dumps(dict(phase=phase, mean_w=round(sum(r['power_w'] for r in rows)/len(rows), 3), energy_delta_w=round((first['energy_wh']-last['energy_wh'])*3600/seconds, 3), cpu_percent=round((last['cpu_usage_usec']-first['cpu_usage_usec'])/seconds/1e4, 2), throttled_periods=last['nr_throttled']-first['nr_throttled'])), flush=True)
    finally:
        ctl('set-property', '--runtime', UNIT, 'CPUQuota=')
        print('Restored Firefox CPU quota to unlimited.', flush=True)

if __name__ == '__main__':
    main()
