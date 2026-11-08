# Laptop snapshot: laptop-rev

Snapshot of the active Lenovo 82XM configuration, 2026-11-07. This is a config
backup, not a tested fresh-machine installation. Active system files were not
changed by the sync. `laptop-snapshot.sha256` records snapshot contents; zshrc has a credential
assignment removed and is intentionally not byte-identical to the live source.

## Active desktop

- Hyprland package: 0.57.1-1. Active entry point: `hypr/hyprland.lua`;
  `theme.lua` reads `colors.conf`. Do not restore the old Hyprlang config.
- Waybar package: 0.15.0-3, but the startup script actually launches a local
  Lua-compatible build at `~/.local/lib/waybar-hyprland-lua/waybar`.
  The binary is not included here. A cached Waybar source checkout exists at
  `~/.cache/yay/waybar-git/src/waybar-git`, commit
  `0d5a4f82eca6df03b73908244d1dcd5fec2c3584`, with no tracked modifications.
  This checkout has not been established as the exact source of the active binary.
  Build/install a compatible Waybar or adapt the launcher after verifying the
  fresh system's packaged Waybar supports the configured Lua dispatchers.
- Native audio widget source is included under `waybar/native/audio-pill`;
  rebuild its shared library on the new system.
- Spotify and calendar integrations depend on separate projects documented in
  README.md. Their source, virtual environments, authentication and data are
  not bundled here. Restore separately or disable those optional modules.

## Laptop scripts and shell

`sys-scripts/battery-power-mode` includes service/timer sources and its installer.
Review it before installation: its installer writes system files and enables a
timer. Merely restoring this directory does not install the service.

The shell prompt belongs under `~/.oh-my-zsh/custom/themes/`. Oh My Zsh and its
plugins must be installed separately. Private `zsh/env.zsh` is excluded.

## Known restore issues to resolve

- Hyprland currently invokes a polkit-gnome agent path. This session instead
  needed the installed KDE polkit agent started manually. Select one available
  agent for the new system; the snapshot deliberately preserves the source config.
- The shell refers to `~/.config/hypr/scripts/theme_changer.sh`, which is absent
  from the active Hyprland directory. Repair or remove that helper on restoration.
- Several integrations contain `/home/v18` or project-specific paths. Adapt them
  if the destination username or project locations change.
- Wallpaper images, generated wallpaper state, credentials, caches, compiled
  binaries and browser profiles are not included. Existing historical files in
  other repository directories are not necessarily active configuration.

The original checkout (including pre-existing uncommitted edits) is backed up at
`/home/v18/current-dots-before-laptop-rev-20261107-222432`. This is on the same USB;
it is not an off-device backup. The branch is local unless explicitly pushed.

For a clean SSD setup, establish a working minimal desktop first, then restore
these configs selectively using INSTALL.md. Do not blindly overwrite a fresh
installation or enable optional services before their dependencies are available.
