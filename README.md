# current-dots

Selected configuration for my Arch Linux / Hyprland desktop. The app directories
mirror the corresponding directories under `~/.config`; `zshrc` mirrors `~/.zshrc`.
Review destination files and back them up before restoring a snapshot.

| Repository path | Restore location |
| --- | --- |
| `hypr`, `waybar`, `sys-scripts`, `style-change` | `~/.config/<directory>` |
| `dunst`, `kitty`, `neofetch`, `nvim`, `rofi`, `wofi` | `~/.config/<directory>` |
| `zshrc` | `~/.zshrc` |
| `zap-prompt.zsh-theme` | `~/.oh-my-zsh/themes/zap-prompt.zsh-theme` |

The snapshot includes workspace audio markers, clock/calendar integration, Rofi
and Neovim themes, the shell prompt, wallpaper scripts, and other desktop updates.
Monitor resolution and placement changes are deliberately excluded from the sync:
`hypr/hyprland.conf` retains the repository's preferred-resolution/automatic-placement
monitor rule. Other paths may still be specific to this machine.
`hypr/hyprland.lua.future` is an inactive draft with its own monitor examples;
review it before activation. It is not the active config.

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

`waybar/scripts/codex_agents.py` is intentionally retained from the repository:
it has tmux and session-name support absent from the live copy, while the live copy
has separate focus/locking fixes. Reconcile those versions before replacing either
one. `sys-scripts/launch-codex-tmux.sh` is also retained even though it is not currently
installed in `~/.config/sys-scripts`.
