-- ShadowOS — Hyprland config
-- On a system installed from the ShadowOS ISO, shadowos-session-start deploys
-- this file again from /etc/shadowos/desktop at every login. Put personal
-- tweaks in ~/.config/hypr/user.lua: it is loaded last and never replaced.

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

-- === Programs ===
local terminal = "shadow-term"
local launcher = "wofi --show drun"
local browser  = "librewolf || firefox"
local files    = "shadow-term -e yazi"

-- === Autostart ===
hl.on("hyprland.start", function()
    hl.exec_cmd("hyprpaper")
    hl.exec_cmd("waybar || (sleep 2 && waybar -c /etc/shadowos/desktop/waybar/config.fallback.jsonc)")
    hl.exec_cmd("mako")
    hl.exec_cmd("hypridle")
    hl.exec_cmd("/usr/lib/polkit-kde-authentication-agent-1")
    hl.exec_cmd("wl-paste --type text  --watch cliphist store")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")
    -- First-run welcome (stamps ~/.config/shadowos/welcome.stamp — no-op afterwards)
    hl.exec_cmd("sleep 2 && /usr/local/bin/shadowos-welcome")
    -- ShadowCypher is opt-in: SUPER+S or the Waybar icon — never a login takeover
end)

-- === Env ===
hl.env("XCURSOR_THEME", "Adwaita")
hl.env("XCURSOR_SIZE", "24")
hl.env("QT_QPA_PLATFORM", "wayland;xcb")
hl.env("MOZ_ENABLE_WAYLAND", "1")
hl.env("GDK_BACKEND", "wayland,x11")
hl.env("SHADOWOS_VERSION", "0.3")

hl.config({
    -- === Input ===
    input = {
        kb_layout    = "us",
        follow_mouse = 1,
        sensitivity  = 0,
        touchpad = {
            natural_scroll       = true,
            disable_while_typing = true,
        },
    },

    -- === Look & feel ===
    -- Border colour follows the active mode — see mode.lua (loaded below).
    general = {
        gaps_in     = 5,
        gaps_out    = 10,
        border_size = 2,
        col = {
            active_border   = { colors = { "rgba(00E0A4FF)", "rgba(00B988FF)" }, angle = 45 },
            inactive_border = "rgba(161B22AA)",
        },
        layout           = "dwindle",
        resize_on_border = true,
    },

    -- Blur/shadow off by default (VM-safe); hardware-adjustments.lua re-enables on bare metal.
    decoration = {
        rounding = 10,
        blur = {
            enabled        = false,
            size           = 8,
            passes         = 3,
            ignore_opacity = true,
        },
        shadow = {
            enabled      = false,
            range        = 24,
            render_power = 3,
            color        = "rgba(00000099)",
        },
        active_opacity   = 1.0,
        inactive_opacity = 0.97,
    },

    animations = {
        enabled = true,
    },

    dwindle = {
        preserve_split = true,
    },

    master = {
        new_status = "master",
        mfact      = 0.55,
    },

    misc = {
        disable_hyprland_logo    = true,
        disable_splash_rendering = true,
        background_color         = "rgb(0D1117)",
        focus_on_activate        = true,
    },
})

hl.curve("smoothOut", { type = "bezier", points = { { 0.36, 0 },   { 0.66, -0.56 } } })
hl.curve("overshoot", { type = "bezier", points = { { 0.05, 0.9 }, { 0.1, 1.05 } } })

hl.animation({ leaf = "windows",    enabled = true, speed = 5,  bezier = "overshoot", style = "slide" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 4,  bezier = "smoothOut", style = "slide" })
hl.animation({ leaf = "border",     enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "fade",       enabled = true, speed = 6,  bezier = "default" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 5,  bezier = "overshoot", style = "slide" })

-- === Window rules ===
hl.window_rule({ name = "float-pavucontrol",  match = { class = "^(org.pulseaudio.pavucontrol|pavucontrol)$" }, float = true })
hl.window_rule({ name = "float-nm-editor",    match = { class = "^(nm-connection-editor)$" },                   float = true })
hl.window_rule({ name = "float-swappy",       match = { class = "^(swappy)$" },                                 float = true })
hl.window_rule({ name = "float-shadow-update", match = { title = "^(shadow-update.*)$" },                       float = true })
hl.window_rule({ name = "suppress-maximize",  match = { class = ".*" }, suppress_event = "maximize" })

-- === Keybinds ===
local mod = "SUPER"

local function run(keys, command, flags)
    hl.bind(keys, hl.dsp.exec_cmd(command), flags)
end

-- Apps
run(mod .. " + Return", terminal)
run(mod .. " + T",      terminal)
run(mod .. " + D",      launcher)
run(mod .. " + B",      browser)
run(mod .. " + E",      files)
run(mod .. " + C",      "shadow-term -e nvim")
run(mod .. " + N",      "shadow-term -e btop")
run(mod .. " + SPACE",  "/usr/local/bin/shadow-ai-overlay")
run(mod .. " + I",      "/usr/local/bin/shadow-settings")
run(mod .. " + S",      "env SHADOWCYPHER_MANUAL=1 /usr/local/bin/shadowcypher-autostart --manual")
run(mod .. " + F1",     "/usr/local/bin/shadowos-tour")

-- Clipboard history
run(mod .. " + V", "cliphist list | wofi --dmenu --prompt clipboard | cliphist decode | wl-copy")

-- ShadowOS modes (normal · privacy · ghost)
run(mod .. " + M",         "/usr/local/bin/shadow-mode picker")
run(mod .. " + SHIFT + M", "pkexec /usr/local/bin/shadow-mode normal")
run(mod .. " + SHIFT + T", "pkexec /usr/local/bin/shadow-mode toggle-tor")

-- Screenshots: region → annotate · full screen → clipboard
run("Print",               'grim -g "$(slurp)" - | swappy -f -')
run(mod .. " + SHIFT + S", 'grim -g "$(slurp)" - | swappy -f -')
run("SHIFT + Print",       'grim - | wl-copy && notify-send "Screenshot" "Full screen copied to clipboard"')

-- Session
run(mod .. " + ESCAPE",      "/usr/local/bin/shadow-power-menu")
run(mod .. " + CTRL + L",    "loginctl lock-session")
hl.bind(mod .. " + SHIFT + E", hl.dsp.exit())
run(mod .. " + SHIFT + F12", "pkexec shadow-bios")

-- Windows
hl.bind(mod .. " + Q",             hl.dsp.window.close())
hl.bind(mod .. " + F",             hl.dsp.window.fullscreen({ mode = "fullscreen" }))
hl.bind(mod .. " + SHIFT + F",     hl.dsp.window.fullscreen({ mode = "maximized" }))
hl.bind(mod .. " + SHIFT + SPACE", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mod .. " + P",             hl.dsp.window.pseudo())
hl.bind(mod .. " + J",             hl.dsp.layout("togglesplit"))

-- Focus, move and resize with the arrow keys
local arrows = {
    left  = { x = -40, y = 0 },
    right = { x = 40,  y = 0 },
    up    = { x = 0,   y = -40 },
    down  = { x = 0,   y = 40 },
}
for direction, step in pairs(arrows) do
    hl.bind(mod .. " + " .. direction,         hl.dsp.focus({ direction = direction }))
    hl.bind(mod .. " + SHIFT + " .. direction, hl.dsp.window.move({ direction = direction }))
    hl.bind(mod .. " + ALT + " .. direction,
        hl.dsp.window.resize({ x = step.x, y = step.y, relative = true }), { repeating = true })
end

-- Workspaces
for i = 1, 10 do
    local key = i % 10 -- workspace 10 is on the 0 key
    hl.bind(mod .. " + " .. key,         hl.dsp.focus({ workspace = i }))
    hl.bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end
hl.bind(mod .. " + TAB",         hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mod .. " + SHIFT + TAB", hl.dsp.focus({ workspace = "e-1" }))
hl.bind(mod .. " + mouse_down",  hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mod .. " + mouse_up",    hl.dsp.focus({ workspace = "e-1" }))

-- Scratchpad
hl.bind(mod .. " + grave",         hl.dsp.workspace.toggle_special("scratch"))
hl.bind(mod .. " + SHIFT + grave", hl.dsp.window.move({ workspace = "special:scratch" }))

-- Mouse
hl.bind(mod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Media / hardware keys
local held   = { locked = true, repeating = true }
local locked = { locked = true }
run("XF86AudioRaiseVolume",  "wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+", held)
run("XF86AudioLowerVolume",  "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-",        held)
run("XF86AudioMute",         "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle",       locked)
run("XF86AudioMicMute",      "wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle",     locked)
run("XF86MonBrightnessUp",   "brightnessctl set 5%+",                            held)
run("XF86MonBrightnessDown", "brightnessctl set 5%-",                            held)
run("XF86AudioPlay",         "playerctl play-pause",                             locked)
run("XF86AudioNext",         "playerctl next",                                   locked)
run("XF86AudioPrev",         "playerctl previous",                               locked)

-- === Per-machine + per-mode overrides (loaded last so they win) ===
local config_home = os.getenv("XDG_CONFIG_HOME")
if not config_home or config_home == "" then
    config_home = os.getenv("HOME") .. "/.config"
end

-- Run one of the files below if it is there. A mistake in one of them is
-- reported once all three have been tried, so that a broken user.lua cannot
-- take the mode colour or the hardware profile with it.
local problems = {}
local function include(name)
    local path = config_home .. "/hypr/" .. name
    local file = io.open(path, "r")
    if not file then
        return
    end
    file:close()
    local ok, err = pcall(dofile, path)
    if not ok then
        problems[#problems + 1] = tostring(err)
    end
end

-- Put in place by shadowos-session-start on each login (VM vs bare-metal effects)
include("hardware-adjustments.lua")
-- Written by shadowos-theme-apply on mode switch (border accent per mode)
include("mode.lua")
-- Personal overrides — never touched by ShadowOS
include("user.lua")

if #problems > 0 then
    error(table.concat(problems, "\n"), 0)
end
