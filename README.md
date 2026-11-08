# current-dots

Selected configuration for my Arch Linux / Hyprland desktop. The app directories
mirror the corresponding directories under `~/.config`; `zshrc` mirrors `~/.zshrc`.
Review destination files and back them up before restoring a snapshot.

**Installing on another machine?** Start with [INSTALL.md](INSTALL.md). It guides
agents through discovery, monitor-layout questions, backups, dependencies,
machine-specific adaptations, validation, and rollback.

| Repository path | Restore location |
| --- | --- |
| `hypr`, `waybar`, `sys-scripts`, `style-change` | `~/.config/<directory>` |
| `dunst`, `kitty`, `neofetch`, `nvim`, `rofi`, `wofi` | `~/.config/<directory>` |
| `zshrc` | `~/.zshrc` |
| `zap-prompt.zsh-theme` | `~/.oh-my-zsh/custom/themes/zap-prompt.zsh-theme` |

The snapshot includes workspace audio markers, clock/calendar integration, Rofi
and Neovim themes, the shell prompt, wallpaper scripts, and other desktop updates.
This branch snapshots the laptop's active Lua configuration in
`hypr/hyprland.lua`, with `theme.lua`, shared colors, lock/idle configuration,
and the current Waybar and supporting scripts. The obsolete Hyprlang entry point
and inactive Lua draft were removed from this branch. See
[LAPTOP-RESTORE.md](LAPTOP-RESTORE.md) for version requirements and known external
dependencies before restoring onto a fresh installation.

## Waybar layout

Volume/microphone and the native audio visualizer share one island on the left,
followed by a separate Spotify island. The clock stays centered. The right side
contains wallpaper changer, desktop/workspaces, Codex tracker, and one combined
CPU/RAM/system-tray island. Adjacent islands have 5px gaps with 12px outer margins.
The tray remains visible outside the updates drawer.

While working, the Codex tracker chooses an orange, blue, or purple background
and scan, then switches to a different color roughly every 30 seconds. Both
monitors share that choice through a locked runtime state file. Inactive
backgrounds keep their existing colors; the tracker uses the standard island
border. The active blue background uses 45% opacity; orange and purple use 60%.
Restore `waybar/scripts/codex_scan_palette.py` beside `codex_agents.py`.
Check the palette behavior with `python3 -m unittest discover -s waybar/tests -v`.

The wallpaper island uses `waybar/wallpaper-cloud-blue.svg` and
`waybar/wallpaper-cloud-lavender.svg` for its animated blue/purple clouds; restore
both alongside `style.css`. The 97px visualizer uses a translucent brown inset
and orange frequency bars. Build it from
[`waybar/native/audio-pill`](waybar/native/audio-pill/README.md) on the destination
machine before starting Waybar; binaries are not included. The older Python
visualizer remains available but is not enabled.

The cloud SVGs embed precomputed seamless textures to avoid SVG noise-filter
seams. Regenerate them from the repository root with
`python3 waybar/scripts/generate_wallpaper_clouds.py waybar`.
Generation uses only Python's standard library; Waybar animates the stored images.

## Spotify widget dependency

The Spotify island uses the native widget from the separate local project at
`~/Documents/Code/projects/spotify-scroll-main`. Build and install its shared
library before restoring this Waybar config:

```sh
cd "$HOME/Documents/Code/projects/spotify-scroll-main"
cargo test --release --locked
cargo build --release --locked
install -Dm755 target/release/libspotify_scroll.so \
  "$HOME/.local/lib/waybar/libspotify_scroll.so"
```

The source project and compiled library are not included in this dots snapshot.
It needs Rust/Cargo and GTK 3 development libraries to build, and `playerctl` at
runtime. No `zscroll` is needed. The `cffi/spotify` entry in `waybar/config.jsonc`
loads the library; adjust its absolute home path on another machine. The widget
keeps the existing `#custom-spotify` CSS and uses a 13-column text viewport.
Long tracks and idle/status messages scroll through the same viewport without
ellipsis (implemented in the local project's `src/cffi.rs`). Pausing a track
freezes its scroll; short text stays still. Click toggles playback;
scroll up/down skips to the next/previous track. Metadata is polled every 500 ms.

## Calendar clock dependency

The task database, calendar synchronization, tooltip formatting, and reminder
logic belong to [cliche-todo](https://github.com/vmad18/cliche-todo). This repository
stores the desktop configuration that calls that app, plus the existing weather
script. The live entry points are:

- `waybar/config.jsonc`: launches `tasks waybar watch` from the app's virtual environment.
- `waybar/style.css`: imports the app's `integrations/waybar-calendar.css`.
- `waybar/scripts/clock_weather.py`: supplies the weather information alongside tasks.

Restore the app at its current checkout path before starting this Waybar config:

```sh
git clone https://github.com/vmad18/cliche-todo "$HOME/Documents/Code/projects/start-up-task-list"
cd "$HOME/Documents/Code/projects/start-up-task-list"
uv sync
```

The current Waybar entries contain `/home/v18/Documents/Code/projects/start-up-task-list`
and `/home/v18/.config/waybar`. Update those entries if the home directory or checkout
path changes. Google authorization and the local task database are set up separately;
follow the app's README. The app also needs PipeWire's `pw-play` for reminder sounds.

## Other restore dependencies

The desktop expects its applications and fonts to be installed, including Hyprland,
Waybar, PipeWire/PulseAudio tools, Kitty, Rofi, and JetBrainsMono Nerd Font. Wallpaper
files under `~/.config/Backgrounds` and the generated `~/.background.md` are outside
this snapshot. The shell also expects Oh My Zsh and its configured plugins. Private
environment values in `~/.config/zsh/env.zsh` are deliberately not mirrored.

Existing historical themes, backups, and old Neovim layout files remain in Git;
they are not all active on this machine. New caches, bytecode, runtime files, and
backup archives are ignored. Sync from selected configuration directories rather
than copying all of `~/.config` into this repository.

On `laptop-rev`, the tracker and launch scripts match the live laptop copies.
The previous repository versions and pre-existing uncommitted work were backed up
outside this repository before synchronization. `main` was not advanced.
