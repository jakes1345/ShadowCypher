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
