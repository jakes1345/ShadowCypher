-- Virtual machine: no blur, shadows or animations, which software rendering
-- makes slow. shadowos-session-start copies this to
-- ~/.config/hypr/hardware-adjustments.lua at every login in a VM.
hl.config({
    decoration = {
        rounding = 0,
        shadow   = { enabled = false },
        blur     = { enabled = false },
    },
    animations = { enabled = false },
})
