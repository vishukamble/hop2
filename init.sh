#!/bin/bash
# hop2 shell integration
# Add this to your ~/.bashrc or ~/.zshrc:
# source ~/.hop2/init.sh

# Main hop2 function that handles directory changes and command shortcuts
hop2() {
    # For known commands, pass through directly
    if [ "$1" = "add" ] || [ "$1" = "cmd" ] || [ "$1" = "list" ] || [ "$1" = "ls" ] || [ "$1" = "rm" ] || [ "$1" = "update-me" ] || [ "$1" = "uninstall-me" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        command hop2 "$@"
        return
    fi

    # For single arg that's not a known command, try as shortcut
    if [ "$#" -eq 1 ]; then
        # Try to use it as a directory shortcut first
        local output
        output=$(command hop2 go "$1" 2>&1)

        if [[ $output == __HOP2_CD:* ]]; then
            # Extract path and cd to it
            local path="${output#__HOP2_CD:}"
            cd "$path" || return 1
        else
            # Not a directory, try as command
            command hop2 "$@"
        fi
    elif [ "$1" = "go" ]; then
        # Explicit go command
        local output
        output=$(command hop2 "$@" 2>&1)

        if [[ $output == __HOP2_CD:* ]]; then
            local path="${output#__HOP2_CD:}"
            cd "$path" || return 1
        else
            echo "$output"
        fi
    else
        # Multi-arg shortcuts (like 'hop2 gs arg1 arg2')
        command hop2 "$@"
    fi
}

# Shorter alias for hop2
alias h2="hop2"

# Even shorter function for jumping to directories: "h <alias>"
h() {
    if [ -z "$1" ]; then
        hop2 list
    else
        hop2 go "$1"
    fi
}

# Bash completion with ALL commands
_hop2_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Main command completion
    if [ "$COMP_CWORD" -eq 1 ]; then
        local commands="add cmd list ls rm update-me uninstall-me"
        local aliases
        aliases=$(sqlite3 ~/.hop2/hop2.db \
            "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null | tr '\n' ' ')
        COMPREPLY=($(compgen -W "$commands $aliases" -- "$cur"))
        return
    fi

    # Subcommand specific completion
    case "$prev" in
        rm|go)
            local aliases
            aliases=$(sqlite3 ~/.hop2/hop2.db \
                "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null | tr '\n' ' ')
            COMPREPLY=($(compgen -W "$aliases" -- "$cur"))
            ;;
    esac
}

if [ -n "$BASH_VERSION" ]; then
    complete -F _hop2_completion hop2
    complete -F _hop2_completion h2
    complete -F _hop2_completion h
fi

# Zsh completion
if [ -n "$ZSH_VERSION" ]; then
    _hop2() {
        local -a all_aliases
        all_aliases=(${(f)"$(sqlite3 ~/.hop2/hop2.db 'SELECT alias FROM directories UNION SELECT alias FROM commands' 2>/dev/null)"})
        _arguments "1:command:(add cmd list ls rm update-me uninstall-me $all_aliases)"
    }
    compdef _hop2 hop2 h2 h
fi

