# Native audio visualizer

Waybar CFFI widget that draws a 97px-wide audio spectrum beside the volume
controls. It uses a translucent matte-brown inset, 9px corners, no inner outline,
and orange dots/bars. The containing grey island supplies the outer border and
backdrop blur. Spotify remains in a separate island.

## Build and install

Requires a C compiler, `pkg-config`, GTK 3 / Cairo and GIO Unix development files,
a Waybar build supporting CFFI v2, and `parec` at runtime. The interface was checked
against [Waybar 0.15.0](https://github.com/Alexays/Waybar/blob/0.15.0/resources/custom_modules/cffi_example/waybar_cffi_module.h).
Verify those dependencies on the destination; this build script installs nothing.

Copy this directory to the target configuration root's `waybar/native/audio-pill`,
then build **on that machine**:

```sh
cd "$HOME/.config/waybar/native/audio-pill"
sh build.sh
```

The output is `build/audio_pill.so`. Set `cffi/audio_pill.module_path` in the
target Waybar config to its **absolute path**. The repo's config uses
`/home/v18/.config/waybar/native/audio-pill/build/audio_pill.so`; adapt the username
and config root. Do not assume the CFFI loader expands `~` or shell variables.

Keep `"embedded": true` and place `cffi/audio_pill` in `group/media.modules`
alongside `pulseaudio`. Removing that entry disables the visualizer without
affecting the volume controls.

Rebuilds replace the library atomically to avoid truncating a mapped binary.
**Fully restart the owning Waybar process after rebuilding**: a config reload
alone can reuse a previously loaded library. Alternatively, use
`sh build.sh build/audio_pill-next.so`, change `module_path` to the new absolute
filename, and reload. Coordinate with the existing bar watcher instead of
starting another Waybar owner. Never overwrite a loaded library in place.
Do not commit or transfer compiled binaries between different systems.

## Signal representation

A single mono 48kHz capture of the default output monitor is shared by widgets
within each Waybar process. It does not record the microphone or write audio to
disk. A 4096-sample Hann-windowed FFT advances by 2048 samples. The 23 bands
cover approximately 40Hz–18kHz, left to right, with window-energy compensation.

Heights use a fixed -60 to -6 dBFS scale; overall unwindowed RMS controls brightness.
There is no adaptive peak normalization or artificial center taper. These represent
captured digital signal levels, not calibrated room loudness.

The GTK timer runs at 20Hz, with quick attack and slower release. Silent,
unchanged frames do not request redraws. Capture retries after disconnects and
stops when the last widget is unloaded.

## Checks

`sh build.sh --check` builds/runs the synthetic signal checks and compiles the
offscreen lifecycle check. Run `build/smoke` in a working graphical/audio session
to check real capture, two widgets sharing one stream, embedded sizing, and
cleanup. It creates offscreen widgets, not a second bar.

Signal checks cover silence, bass/midrange/treble placement, equal-amplitude
tones, mixed tones, a 20dB level change, and independence from previous peaks.
The reported analysis benchmark excludes GTK redraw and capture costs.

An optional illustrative preview can be built with:

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror -DAUDIO_PREVIEW audio_pill.c -o build/preview $(pkg-config --cflags --libs gtk+-3.0 gio-unix-2.0) -lm
build/preview build/preview.png
```

The preview's sample levels are illustrative. The accepted embedded appearance
should be checked in Waybar, where the parent island paints the grey background.
