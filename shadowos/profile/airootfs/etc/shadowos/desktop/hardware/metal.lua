-- Real hardware: full effects (hyprland.lua leaves them off, to be safe in a
-- VM). shadowos-session-start copies this to
-- ~/.config/hypr/hardware-adjustments.lua at every login on real hardware.
hl.config({
    decoration = {
        rounding = 10,
        shadow = {
            enabled      = true,
            range        = 24,
            render_power = 3,
            color        = "rgba(00000099)",
        },
        blur = {
            enabled        = true,
            size           = 8,
            passes         = 3,
            ignore_opacity = true,
            vibrancy       = 0,
        },
    },
    animations = { enabled = true },
})
