# ShadowOS default zsh config
autoload -Uz compinit && compinit
setopt autocd interactivecomments hist_ignore_dups share_history
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000

# Aliases
alias ls='eza --group-directories-first --icons'
alias ll='eza -l --group-directories-first --icons --git'
alias la='eza -la --group-directories-first --icons --git'
alias cat='bat --paging=never --style=plain'
alias grep='rg'
alias find='fd'

alias mode='shadow-mode'
alias leak='shadow-leak-test'
alias tor-status='systemctl status tor --no-pager'

# Welcome banner on first prompt of new terminals
if [[ -z "$SHADOWOS_GREETED" && -t 1 ]]; then
    export SHADOWOS_GREETED=1
    fastfetch --config /etc/fastfetch/shadowos.jsonc 2>/dev/null || true
fi

# Starship prompt
command -v starship >/dev/null 2>&1 && eval "$(starship init zsh)"
alias watch='shadow-stream'

# --- ShadowOS Tactical Aliases ---
alias wipe='shadow-wipe'
alias ports='rustscan -a'
alias recon='subfinder -d $1 | httpx'
alias lls='ls -lah --color=auto'
alias search='grep -rnw . -e'
alias myip='curl -s https://ifconfig.me && echo'

# === Omarchy-inspired shell setup ===

# zoxide — smart cd (learns most-visited dirs, replaces cd)
command -v zoxide >/dev/null 2>&1 && eval "$(zoxide init zsh)" && alias cd='z'

# atuin — shell history with fuzzy search (replaces ctrl+r)
command -v atuin >/dev/null 2>&1 && eval "$(atuin init zsh)"

# yazi — shell wrapper: cd to last dir when exiting yazi
yy() {
    local tmp
    tmp="$(mktemp -t "yazi-cwd.XXXXX")"
    yazi "$@" --cwd-file="$tmp"
    if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
        builtin cd -- "$cwd" || true
    fi
    rm -f -- "$tmp"
}

# === Privacy / AnonSurf aliases (Parrot-inspired) ===
alias anonsurf='sudo shadow-anonsurf'
alias anon-start='sudo shadow-anonsurf start'
alias anon-stop='sudo shadow-anonsurf stop'
alias anon-check='shadow-anonsurf check'
alias anon-status='shadow-anonsurf status'
alias myip='torsocks curl -s https://api.ipify.org && echo'
alias realip='curl -s https://api.ipify.org && echo'

# === Qubes VM aliases ===
alias qube='sudo shadow-qube'
alias qube-disp='sudo shadow-qube disposable'
alias qube-list='shadow-qube list'

# === SteamOS / Gaming aliases ===
alias game='shadow-gamescope'
alias steam-bp='shadow-gamescope'

# === Amnesia / Tails aliases ===
alias amnesia='sudo /etc/shadowos/modes/amnesia/apply.sh'

# Safer rm (move to trash instead of delete)
alias rm='rm -I'

# Modern tool replacements (omarchy-style)
alias ps='procs'
alias du='gdu'
alias diff='diff --color=always'
