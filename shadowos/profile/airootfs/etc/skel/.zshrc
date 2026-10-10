# ShadowOS — zsh config (fast, minimal). Personal additions: ~/.zshrc.local

# === History ===
HISTFILE=~/.zsh_history
HISTSIZE=50000
SAVEHIST=50000
setopt share_history hist_ignore_all_dups hist_ignore_space hist_reduce_blanks extended_history

# === Shell options ===
setopt autocd interactive_comments no_beep
bindkey -e

# === Completion ===
autoload -Uz compinit && compinit
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"

# === Environment ===
export EDITOR=nvim
export VISUAL=nvim
export PAGER=less
export MANPAGER="sh -c 'col -bx | bat -l man -p'"
export MANROFFOPT="-c"
export BAT_THEME="ansi"

# === Aliases ===
alias ls='eza --icons --group-directories-first'
alias ll='eza -l --icons --group-directories-first --git'
alias la='eza -la --icons --group-directories-first --git'
alias lt='eza --tree --level=2 --icons --group-directories-first'
alias cat='bat --paging=never --style=plain'
alias ..='cd ..'
alias ...='cd ../..'
alias v='nvim'
alias rm='rm -I'
alias diff='diff --color=auto'
alias ip='ip -color=auto'

# ShadowOS
alias mode='shadow-mode'
alias leak='shadow-leak-test'
alias tor-status='systemctl status tor --no-pager'
alias myip='curl -s https://api.ipify.org; echo'
alias torip='torsocks curl -s https://api.ipify.org; echo'
alias ff='fastfetch'

# yazi: cd into the last directory on exit
yy() {
    local tmp cwd
    tmp="$(mktemp -t yazi-cwd.XXXXXX)"
    yazi "$@" --cwd-file="$tmp"
    if cwd="$(<"$tmp")" && [[ -n "$cwd" && "$cwd" != "$PWD" ]]; then
        builtin cd -- "$cwd"
    fi
    rm -f -- "$tmp"
}

# === Tools ===
# fzf: Ctrl-R history, Ctrl-T files, Alt-C cd
if command -v fzf >/dev/null; then
    export FZF_DEFAULT_COMMAND='fd --type f --hidden --exclude .git'
    export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
    export FZF_DEFAULT_OPTS='--height 40% --layout=reverse --border
      --color=bg+:#161B22,fg+:#E6EDF3,hl:#00E0A4,hl+:#00E0A4,pointer:#00E0A4,prompt:#00E0A4,info:#8B949E,border:#30363D'
    if fzf --zsh >/dev/null 2>&1; then
        source <(fzf --zsh)
    else
        [[ -f /usr/share/fzf/key-bindings.zsh ]] && source /usr/share/fzf/key-bindings.zsh
        [[ -f /usr/share/fzf/completion.zsh ]]   && source /usr/share/fzf/completion.zsh
    fi
fi

# zoxide: cd learns frequent dirs (cd <partial>, cdi for interactive picker)
command -v zoxide >/dev/null && eval "$(zoxide init zsh --cmd cd)"

# === Plugins ===
[[ -f /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && \
    source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#484F58'

# === Prompt ===
command -v starship >/dev/null && eval "$(starship init zsh)"

# === Greeting: one line, once per terminal window ===
if [[ -o interactive && -z "$SHADOWOS_GREETED" && -z "$TMUX" ]]; then
    export SHADOWOS_GREETED=1
    () {
        local m=normal c=$'\e[38;2;230;237;243m'
        [[ -r /var/lib/shadowos/current-mode ]] && m="$(</var/lib/shadowos/current-mode)"
        case "$m" in
            privacy) c=$'\e[38;2;244;162;97m' ;;
            ghost)   c=$'\e[38;2;230;57;70m' ;;
        esac
        print -P "%F{#00E0A4}%B ShadowOS%b%f  %F{#484F58}·%f  mode ${c}${m}"$'\e[0m'"  %F{#484F58}·  SUPER+M to switch · F1 for help%f"
    }
fi

# Local overrides
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

# syntax-highlighting must be sourced last
[[ -f /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && \
    source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
