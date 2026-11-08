-- Personal configuration migrated to Hyprland 0.57's Lua API.
-- Palette values are shared with hyprlock through colors.conf.
local config_dir = debug.getinfo(1, "S").source:sub(2):match("(.*/)")
local colors = dofile(config_dir .. "theme.lua")

hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XCURSOR_SIZE", "24")

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

hl.config({
    input = {
        kb_layout = "us",
        kb_variant = "",
        kb_model = "",
        kb_options = "",
        kb_rules = "",
        follow_mouse = 1,
        sensitivity = 0,
        touchpad = { natural_scroll = false },
    },
    general = {
        gaps_in = 5,
        gaps_out = 15,
        border_size = 2,
        layout = "dwindle",
        col = {
            active_border = colors.active_border,
            inactive_border = colors.inactive_border,
        },
    },
    misc = { disable_hyprland_logo = true },
    decoration = {
        blur = {
            enabled = true,
            size = 7,
            passes = 3,
            new_optimizations = true,
            ignore_opacity = false,
        },
        shadow = {
            enabled = true,
            range = 4,
            render_power = 3,
            color = "rgba(1a1a1aee)",
        },
    },
    animations = { enabled = true },
    dwindle = { preserve_split = true },
})

hl.device({ name = "epic-mouse-v1", sensitivity = -0.5 })

hl.curve("curve",     { type = "bezier", points = {{0.76, 0}, {0.24, 1}} })
hl.curve("smoothIn",  { type = "bezier", points = {{0.25, 1}, {0.5, 1}} })
hl.curve("smoothOut", { type = "bezier", points = {{0.36, 0}, {0.66, -0.56}} })
hl.curve("myBezier",  { type = "bezier", points = {{0.05, 0.9}, {0.1, 1.05}} })
hl.curve("liner",     { type = "bezier", points = {{1, 1}, {1, 1}} })

hl.animation({ leaf = "windows",    enabled = true, speed = 5,  bezier = "myBezier" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 4,  bezier = "smoothOut" })
hl.animation({ leaf = "fade",       enabled = true, speed = 10, bezier = "smoothIn" })
hl.animation({ leaf = "fadeDim",    enabled = true, speed = 10, bezier = "smoothIn" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 6,  bezier = "curve", style = "slidevert" })
hl.animation({ leaf = "border",     enabled = true, speed = 10, bezier = "liner" })
hl.animation({ leaf = "borderangle",enabled = true, speed = 35, bezier = "liner", style = "loop" })

hl.window_rule({ name = "chat-opacity", match = { class = "^(Slack|WebCord)$" }, opacity = "0.94 0.94" })
hl.window_rule({ name = "spotify-opacity", match = { class = "^(Spotify)$" }, opacity = "0.7 0.7" })
hl.window_rule({ name = "code-opacity", match = { class = "^(Code)$" }, opacity = "0.9 0.9" })
hl.window_rule({
    name = "hide-xwaylandvideobridge",
    match = { class = "^(xwaylandvideobridge)$" },
    opacity = "0.0 override 0.0 override",
    no_anim = true,
    no_focus = true,
    no_initial_focus = true,
})

hl.layer_rule({ name = "waybar-blur", match = { namespace = "waybar" }, blur = true, ignore_alpha = 0.05 })
-- Spotify and Code are windows, so their blur is handled by decoration.blur.

local mainMod = "SUPER"
local function exec(key, command)
    hl.bind(mainMod .. " + " .. key, hl.dsp.exec_cmd(command))
end

exec("RETURN", "kitty")
hl.bind(mainMod .. " + W", hl.dsp.window.close())
exec("L", "pidof hyprlock || hyprlock --grace 2")
exec("K", "nmcli device disconnect wlan0 && (pidof hyprlock || hyprlock --grace 2)")
exec("O", "nmcli device connect wlan0")
exec("M", "wlogout --protocol layer-shell")
hl.bind(mainMod .. " + SHIFT + M", hl.dsp.exit())
hl.bind(mainMod .. " + F", hl.dsp.window.fullscreen())
exec("E", "nautilus")
exec("V", "/usr/bin/python3 ~/.config/sys-scripts/toggle_floating.py")
exec("SPACE", "wofi")
hl.bind(mainMod .. " + P", hl.dsp.window.pseudo())
hl.bind(mainMod .. " + J", hl.dsp.layout("togglesplit"))
exec("S", [[grim -g "$(slurp)" - | swappy -f -]])
exec("C", "pkill wlsunset || wlsunset -T 4500")

hl.bind("code:121", hl.dsp.exec_cmd("pamixer -t"))
hl.bind("code:122", hl.dsp.exec_cmd("pamixer -d 5"))
hl.bind("code:123", hl.dsp.exec_cmd("pamixer -i 5"))
hl.bind("code:256", hl.dsp.exec_cmd("pamixer --default-source -t"))
hl.bind("code:232", hl.dsp.exec_cmd("brightnessctl set 10%-"))
hl.bind("code:233", hl.dsp.exec_cmd("brightnessctl set 10%+"))

for _, direction in ipairs({"left", "right", "up", "down"}) do
    hl.bind(mainMod .. " + " .. direction, hl.dsp.focus({ direction = direction }))
end

for i = 1, 10 do
    local key = i % 10
    hl.bind(mainMod .. " + " .. key, hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i, follow = true }))
end

hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }))
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

hl.on("hyprland.start", function()
    hl.exec_cmd("awww-daemon")
    hl.exec_cmd("nm-applet")
    hl.exec_cmd("dunst")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("python3 ~/.config/waybar/scripts/workspace_audio.py")
    hl.exec_cmd("bash ~/.config/hypr/xdg-portal-hyprland")
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    hl.exec_cmd("systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    hl.exec_cmd("/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1")
    hl.exec_cmd("hyprctl setcursor Breeze 24")
    hl.exec_cmd("sh ~/.config/sys-scripts/launch-waybar.sh")
end)
