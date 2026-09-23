# Installing current-dots: instructions for agents

Use this guide when a user asks you to install this repository on a new machine.
This is a selected personal configuration snapshot, **not a portable unattended
installer**. Adapt it to the destination machine; do not reproduce the original
machine's hardware assumptions.

A useful request to an agent is:

> Read INSTALL.md and README.md, inspect this machine, and install the selected
> dots. Ask me which display is primary and how my monitors are arranged before
> changing display settings. Preserve existing configuration and provide rollback.

## 1. Establish scope and inspect before changing anything

Read [README.md](README.md), applicable agent instructions, and the target configs.
Inspect Git status and preserve staged or unrelated changes. Do not install the
repository's `.codex` directory as the new user's global agent instructions.

Determine the actual user, home directory, checkout path, and configuration root
(`XDG_CONFIG_HOME`, normally `~/.config`). Inspect the OS, compositor version,
GPU/driver, session, input devices, and existing startup ownership. Useful
read-only commands, when installed and applicable:

```sh
id -un
uname -m
cat /etc/os-release
Hyprland --version
waybar --version
lspci -k
```

In a running Hyprland session:

```sh
hyprctl version
hyprctl -j monitors all
hyprctl -j devices
hyprctl configerrors
pgrep -a -x waybar
```

If Hyprland is not running, do not interpret failed IPC calls as "no monitors."
Use available connector/EDID information and ask the user, or finish display
discovery in a minimal working session first. Do not start a second compositor
inside the user's active desktop.

Confirm the installation scope: desktop only, or also shell/editor configs.
Ask about keyboard layout, desired optional integrations, and wallpaper files
when not already specified. Existing answers remain valid; do not repeatedly ask
for approval of the same scoped work. Ask before unapproved package installation,
sudo, driver changes, service changes, or replacing the user's login shell.

## 2. Resolve compositor compatibility first

This repository's active snapshot is `hypr/hyprland.conf`. It also contains
`hypr/hyprland.lua.future`, an **inactive draft**, not a ready-made replacement.

Check the installed version's syntax and active config path. Current upstream
documentation uses Lua, while the archived 0.54 documentation describes the
hyprlang syntax used by this snapshot. Do not blindly paste legacy rules into
Lua, activate the draft, or downgrade the system to fit the snapshot. If migration
is needed, prepare and validate it against the installed version before activation.

Use the [current configuration reference](https://wiki.hypr.land/configuring/core/)
and the [versioned monitor reference](https://wiki.hypr.land/0.54.0/Configuring/Monitors/).
Other rules, dispatchers, environment settings, and scripts using `hyprctl`
also need compatibility review; translating only the monitor lines is insufficient.

## 3. Discover monitors, then ask the user for their layout

**Never copy connector names, resolutions, refresh rates, rotations, or positions
from the repository's examples or a previous machine.** The active fallback
monitor rule is not evidence of the intended new layout.

Collect connected output names, model/description, supported modes, current
refresh rate, scale, transform, and position. Present recognizable model names
alongside connector names. Ask the user to resolve only what inspection cannot:

- Which physical display is the main one for work, initial workspace/focus, and
  application launching?
- Where is each other display: left/right/above/below? Should top edges, centers,
  or bottom edges line up?
- Which displays are landscape or portrait? For portrait, which way is the screen
  physically rotated?
- What resolution, refresh rate, and scaling do they want on each? Offer detected
  preferred modes as defaults; do not choose the maximum refresh rate blindly.
- Should Waybar appear on all displays or only the main one? Extend or mirror?
  On a laptop, should the internal screen stay on while docked?

Record a concrete proposed table before applying display settings:

| Output / model | Main? | Mode / Hz | Scale | Rotation | Logical position | Waybar? |
| --- | --- | --- | --- | --- | --- | --- |
| Populate from this machine and the user's answers | | | | | | |

Compute placement from **logical dimensions after rotation and scaling**.
For example, a 3840×2160 landscape display at scale 2 occupies 1920×1080 logical
units. A 1920×1080 display rotated 90 degrees at scale 1 occupies 1080×1920.
A top-aligned display immediately to the right of the first starts at `1920x0`.
For vertical centering, offset by half the logical-height difference. Account for
the compositor's supported scale values and rounding; do not leave unintended
gaps or overlaps.

For **hyprlang-compatible versions only**, this is an illustrative layout, not
a command to apply to an unidentified machine:

```ini
# Example only: main 4K display at scale 2, portrait secondary to its right.
monitor = DP-1,3840x2160@60,0x0,2
monitor = HDMI-A-1,1920x1080@60,1920x0,1,transform,1
```

Verify the transform direction with the user. Confirm both modes are advertised.
Use [monitor positioning](https://wiki.hypr.land/configuring/core/monitors/positioning/)
and the [monitor reference](https://wiki.hypr.land/configuring/core/monitors/)
for the installed version.

Treat "main monitor" as a requested behavior, not simply the first output listed:
configure the chosen startup workspace/focus, any requested workspace bindings,
and Waybar output selection. Do not invent a generic `primary=true` monitor rule
or pin every workspace unless requested.

Keep the original working display config recoverable. Before applying a mode
change, prepare a timed rollback or another tested recovery route such as an
accessible TTY and exact restore commands. Keep at least one known-working display
enabled. If the user has not answered the layout questions, leave display settings
unchanged and continue independent staging work.

## 4. Back up and stage the selected files

Prepare changes in a separate staging directory first: Hyprland can reload on
file changes, so copying into its active directory is not a harmless dry run.

Before overwriting a destination, record its type (file/directory/symlink), target,
permissions, and whether it existed. Store a timestamped backup outside the repo,
preserving symlinks and metadata. Keep a manifest of installed and newly created
paths so rollback can restore replaced files and remove only newly installed files.
Do not delete unrelated destination files.

For each selected component, inspect and copy only the active files it needs:

| Source | Destination / handling |
| --- | --- |
| `hypr/` | Target config root's `hypr/`; adapt hardware, version, startup and paths first |
| `waybar/config.jsonc`, `style.css`, `colors.css` | Target `waybar/` |
| `waybar/wallpaper-cloud-blue.svg`, `wallpaper-cloud-lavender.svg` | Beside the Waybar stylesheet; required by its relative URLs |
| `waybar/scripts/` | Reviewed Python scripts only; exclude bytecode and caches |
| `waybar/native/audio-pill/` | Copy source/build instructions, build on the target, and adapt the CFFI library path |
| `sys-scripts/` | Selected scripts referenced by the enabled configuration |
| `style-change/` | Only if theme switching is wanted; inspect what its scripts overwrite |
| `kitty/`, `dunst/`, `rofi/`, `wofi/` | Selected app configs under the target config root |
| `nvim/`, `neofetch/` | Optional; inspect the active entry points and dependencies |
| `zshrc`, `zap-prompt.zsh-theme`, `zsh/` | Optional shell setup; adapt paths and plugin installation |

Do not blanket-copy the repo or all of an old `~/.config`. Exclude `.git`,
`.codex`, backups, experiments, caches, `__pycache__`, historical unused themes,
`oh-my-zsh.zip`, runtime state, and unused animation assets. Do not migrate
credentials, browser profiles, SSH keys, tokens, or unrelated personal files.
Do not inspect private files merely to fill in missing installation details.

Prefer reviewed copies for machine-specific configs. If using symlinks, explain
that runtime edits affect the checkout and do not follow or overwrite pre-existing
symlink targets without inspecting them.

## 5. Resolve dependencies by enabled feature

Inspect what is already installed and use the destination distribution's tooling.
These are capabilities/commands to check, not a blindly executable package list.
Verify current package names and availability before proposing installation.

| Feature | Capabilities to verify |
| --- | --- |
| Desktop | Compatible Hyprland, Waybar, Kitty, chosen launcher, Dunst, Python 3 |
| Fonts/images | JetBrainsMono Nerd Font, configured icon/cursor fonts and themes, GTK SVG loader supporting embedded PNG images |
| Audio | Running audio server, `pactl`, `pamixer`, `parec` for the enabled native visualizer |
| Native visualizer build | C compiler, `pkg-config`, GTK 3/Cairo/GIO Unix development files, Waybar CFFI v2 support |
| Spotify island | Spotify/MPRIS player, `playerctl`, `zscroll` |
| Wallpaper | `awww` and `awww-daemon`, user-provided image files |
| Bar watcher | `inotifywait`, `logger`, `killall`; inspect the watcher before starting |
| Lock/idle | Hyprlock, Hypridle, working lock authentication and chosen idle behavior |
| Desktop integration | Suitable portal backend and one working polkit agent |
| Optional bindings | `grim`, `slurp`, `swappy`, `brightnessctl`, `wlogout`, `nautilus`, `wlsunset` as actually enabled |
| Hardware popup/updates | `vtop`; update script assumes Arch's `pacman` and `yay` |
| Calendar clock | Separate cliche-todo app, its Python environment and `pw-play` |
| Optional shell/editor | Zsh, Oh My Zsh and named plugins; Neovim/plugin requirements; review network bootstrapping before launch |

Disable or adapt unavailable optional modules instead of leaving restart loops.
Do not run an update click handler as a dependency test: it can start a system
upgrade. Do not extract the bundled shell archive or install every historical
theme dependency by default.

## 6. Adapt the known machine-specific details

- **GPU:** `hypr/hyprland.conf` sets NVIDIA-related environment variables. Verify
  the destination GPU/driver before retaining them; check `nvidia-smi` only on an
  NVIDIA system. Follow current vendor/compositor guidance. Never install drivers
  or copy NVIDIA settings onto AMD/Intel machines as part of a blind dotfile copy.
- **Paths:** inspect active files for `/home/v18`, `~/.config`, fixed application
  checkouts, and missing scripts. Rewrite the staged config for the real home and
  config root. Do not use a global string replacement across unrelated files.
  Python strings do not automatically expand `~`; GTK CSS imports need a usable
  resolved path rather than a shell variable.
- **Calendar:** install the app described in README only if wanted, update both
  the Waybar command and CSS import, and configure timezone/weather location.
  Auth and task data are separate; never copy another machine's OAuth/session data.
  If omitted, use the built-in Waybar clock and remove the missing app CSS import
  from the staged stylesheet. A broken absolute import is not an acceptable fallback.
- **Wallpaper:** images are not included. Replace the hard-coded theme image list
  with existing user-selected files. Adapt `background_only.py`'s two absolute
  state paths. Its `next_idx.txt` must contain a valid integer before first use;
  initialize to `0` only if absent. Do not overwrite existing state. Check
  `randbg.sh` path quoting, especially for filenames with spaces. It creates
  `~/.background` and `~/.background.md`; the lockscreen also references an
  unbundled `astro.jpg`.
- **Network/idle:** `wlan0` appears in Hyprland bindings and Hypridle's network
  disconnect action. Ask whether disconnect-on-idle is wanted; do not merely
  substitute an interface name and enable it. Preserve the working network.
- **Startup:** the portal helper kills/restarts portal processes, and a polkit
  path is hard-coded. Use the destination's appropriate session/service ownership;
  do not introduce duplicate agents or portal restarts just to match the file.
- **Executability:** some scripts, including the portal helper and Spotify status
  script, are tracked without executable bits despite direct invocation. Inspect
  the call chain. Use explicit interpreters or narrowly set executable permission
  on reviewed destination scripts with authorization; never `chmod -R`.
- **Bar ownership:** the supplied Waybar watcher uses `killall waybar` and watches
  only config/CSS files, not SVGs. Use one owner for startup/restart; do not launch
  a second watcher per monitor. Reload the intended bar after changing SVG assets.
- **Native visualizer:** follow [its build guide](waybar/native/audio-pill/README.md).
  Copy the source to the target Waybar directory, run `sh build.sh` there, and
  set `cffi/audio_pill.module_path` to the resulting absolute library path before
  enabling it. Rebuild on each destination; never transfer a stale compiled
  binary or an old `.experiments` path. If unavailable, remove `cffi/audio_pill`
  from `group/media.modules` and keep the volume control working. Fully restart
  the owning Waybar process after rebuilding the same library path, or load a
  new filename. A config reload alone can reuse the old library.
- **Agent tracker:** README documents intentional differences between the repo's
  tracker and the original live copy. Preserve/review that implementation. Set up
  its expected local integration separately; do not migrate Codex credentials.
  Install `codex_scan_palette.py` alongside `codex_agents.py`. The helper shares
  active colors across monitors and changes them about every 30 seconds. Its
  `scan-palette.json` is generated under the tracker's runtime directory; do not
  copy that state from another machine or persist it in the dotfiles repository.
- **Shell:** review hard-coded Java/ML/SDK paths, custom aliases, plugin paths, and
  missing shell helpers before replacing `.zshrc`. Installing dots does not
  authorize changing the login shell.
- **Input:** review the named mouse override and keyboard/touchpad settings;
  remove or adapt device-specific examples only in the staged destination config.

The left side contains volume/native visualizer, Spotify, then the Codex tracker.
The clock is centered; wallpaper/desktop/hardware/tray are on the right.
Preserve these choices unless the user requests something else.

## 7. Activate, verify, and recover

Show the concrete destination diff, dependency actions, and monitor table before
any still-unapproved disruptive operation. Apply the already authorized plan
without redundant confirmation. Do not log out, reboot, change services, or lock
the user out merely to test configuration.

Validate syntax and all referenced files before activation. JSONC permits comments;
a strict JSON parser alone is not sufficient. Parse Python without running
long-lived helpers; load the stylesheet with GTK and test the SVG loader. Then
activate one component at a time. Hyprland may auto-reload when its files change.
For explicit reload and diagnostics, consult the installed version's
[hyprctl reference](https://wiki.hypr.land/configuring/core/advanced-configuration/using-hyprctl/).

After activation:

- Check compositor config errors and actual monitor modes, refresh, scale,
  rotation, and positions. Have the user confirm cursor crossings and the primary
  display behavior; syntax validity does not prove the physical arrangement.
- Confirm one intended Waybar owner, bars on the chosen displays, correct fonts,
  readable icons, no missing SVGs, and no helper restart loops.
- Check volume/mic controls and Spotify behavior with user-appropriate audio.
  Check calendar/weather if installed; verify reminder deduplication across displays.
- Confirm wallpaper cycling uses real files. Check terminal/launcher keybindings,
  workspace movement and tracker behavior only for installed integrations.
- Test lock/unlock and sleep/resume only with the user ready and a recovery path;
  do not trigger network disconnects as a smoke test.
- Recheck after a user-approved login/restart if startup behavior remains untested.

On failure, stop the component you started, restore its backed-up files/symlinks
and permissions, remove only files recorded as newly installed, and reload the
previous working configuration. For a black screen, use the prepared recovery
route to restore the display config; do not keep guessing resolutions blindly.

Finish with a short handoff: changed paths, backup location and exact restore
commands, approved monitor table, dependencies installed/skipped, optional features
disabled, checks that passed, and anything still awaiting user validation. Never
report a fresh-machine install as tested when only static configuration checks ran.
