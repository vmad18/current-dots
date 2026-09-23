#!/bin/sh
# Build locally; never truncate the library currently mapped by Waybar.
set -eu
cd -- "$(dirname -- "$0")"
check=false
if [ "${1:-}" = "--check" ]; then
    check=true
    shift
fi
if [ "$#" -gt 1 ]; then
    echo "Usage: sh build.sh [--check] [output.so]" >&2
    exit 2
fi
output=${1:-build/audio_pill.so}
mkdir -p -- "$(dirname -- "$output")"
temporary=$(mktemp "${output}.tmp.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
trap 'exit 1' HUP INT TERM
flags=$(pkg-config --cflags --libs gtk+-3.0 gio-unix-2.0)
# pkg-config supplies compiler words; intentional field splitting here.
cc -std=c11 -O2 -Wall -Wextra -Werror -shared -fPIC audio_pill.c -o "$temporary" $flags -lm
mv -f -- "$temporary" "$output"
echo "Built $output"
if [ "$check" = true ]; then
    mkdir -p build
    cc -std=c11 -O2 -Wall -Wextra -Werror analysis_test.c -o build/analysis_test $flags -lm
    cc -std=c11 -O2 -Wall -Wextra -Werror smoke.c -o build/smoke $flags -lm
    build/analysis_test
    echo "Run build/smoke in the graphical/audio session for the lifecycle check."
fi
