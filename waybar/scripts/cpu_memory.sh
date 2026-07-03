#!/bin/sh

state_dir=${XDG_RUNTIME_DIR:-}

if [ -z "$state_dir" ] || [ ! -d "$state_dir" ] || [ ! -w "$state_dir" ]; then
  state_dir="${XDG_CACHE_HOME:-$HOME/.cache}"
  mkdir -p "$state_dir" 2>/dev/null || state_dir="/tmp"
fi

state_file="$state_dir/waybar-cpu-memory-mode"
request=$1

if [ "$request" = "toggle" ]; then
  current="percent"
  if [ -r "$state_file" ]; then
    current=$(cat "$state_file")
  fi

  if [ "$current" = "gb" ]; then
    printf 'percent\n' > "$state_file"
  else
    printf 'gb\n' > "$state_file"
  fi

  exit 0
fi

read_cpu() {
  awk '/^cpu / {
    idle = $5
    total = 0
    for (i = 2; i <= NF; i++) {
      total += $i
    }
    print idle, total
  }' /proc/stat
}

set -- $(read_cpu)
idle1=$1
total1=$2

sleep 0.2

set -- $(read_cpu)
idle2=$1
total2=$2

total_delta=$((total2 - total1))
idle_delta=$((idle2 - idle1))

if [ "$total_delta" -gt 0 ]; then
  cpu_pct=$(((100 * (total_delta - idle_delta) + total_delta / 2) / total_delta))
else
  cpu_pct=0
fi

set -- $(awk '
  /^MemTotal:/ { total = $2 }
  /^MemFree:/ { free = $2 }
  /^Buffers:/ { buffers = $2 }
  /^Cached:/ { cached = $2 }
  /^SReclaimable:/ { sreclaimable = $2 }
  /^Shmem:/ { shmem = $2 }
  /^SwapTotal:/ { swap_total = $2 }
  /^SwapFree:/ { swap_free = $2 }
  END {
    used = total - free - buffers - cached - sreclaimable + shmem
    if (used < 0) {
      used = 0
    }

    swap_used = swap_total - swap_free
    mem_pct = int((used * 100 + total / 2) / total)
    swap_pct = swap_total ? int((swap_used * 100 + swap_total / 2) / swap_total) : 0

    printf "%d %.1f %.1f %d %.1f %.1f\n",
      mem_pct, used / 1048576, total / 1048576,
      swap_pct, swap_used / 1048576, swap_total / 1048576
  }
' /proc/meminfo)

mem_pct=$1
mem_used=$2
mem_total=$3
swap_pct=$4
swap_used=$5
swap_total=$6

mode="percent"
if [ -r "$state_file" ]; then
  mode=$(cat "$state_file")
fi

if [ "$mode" = "gb" ]; then
  mem_text="${mem_used}G"
else
  mem_text="${mem_pct}%"
fi

gpu_text="󰢮 --"
gpu_tip="GPU: unavailable"
class="no-gpu"

if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_stats=$(
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null |
      awk -F, '
        function trim(value) {
          gsub(/^[ \t]+|[ \t]+$/, "", value)
          return value
        }

        NF >= 3 {
          util = trim($1) + 0
          used = trim($2) + 0
          total = trim($3) + 0

          count++
          used_sum += used
          total_sum += total

          if (util > util_max) {
            util_max = util
          }
        }

        END {
          if (count > 0 && total_sum > 0) {
            vram_pct = int((used_sum * 100 + total_sum / 2) / total_sum)
            printf "%d %.1f %.1f %d\n", util_max, used_sum / 1024, total_sum / 1024, vram_pct
          }
        }
      '
  )

  if [ -n "$gpu_stats" ]; then
    set -- $gpu_stats
    gpu_pct=$1
    vram_used=$2
    vram_total=$3
    vram_pct=$4

    if [ "$mode" = "gb" ]; then
      vram_text="${vram_used}G"
    else
      vram_text="${vram_pct}%"
    fi

    gpu_text="󰢮 ${gpu_pct}%  ${vram_text}"
    gpu_tip="GPU: ${gpu_pct}%\\nVRAM: ${vram_used}/${vram_total} GiB (${vram_pct}%)"
    class="normal"
  fi
fi

if [ "$request" = "gpu" ]; then
  printf '{"text":"%s","tooltip":"%s","class":"%s"}\n' \
    "$gpu_text" "$gpu_tip" "$class"
else
  printf '{"text":" %s%% 󰾆 %s","tooltip":"CPU: %s%%\\nRAM: %s/%s GiB\\nSwap: %s/%s GiB (%s%%)","class":"normal"}\n' \
    "$cpu_pct" "$mem_text" "$cpu_pct" "$mem_used" "$mem_total" "$swap_used" "$swap_total" "$swap_pct"
fi
