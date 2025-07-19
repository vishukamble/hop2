#!/bin/bash
# hop2 shell integration
# Add this to your ~/.bashrc or ~/.zshrc:
#   source ~/.hop2/hop2.sh

# Main hop2 function that handles directory changes and command shortcuts
hop2() {
    if [ "$1" = "go" ] || [ -z "$1" ]; then
        # Use `go` or empty first arg to trigger cd logic
        local output
        output=$(command hop2 "$@" 2>&1)

        if [[ $output == __HOP2_CD:* ]]; then
            # Extract path and cd to it
            local path="${output#__HOP2_CD:}"
            cd "$path" || return 1
        else
            # Not a cd marker, just print whatever hop2.py printed
            echo "$output"
        fi
    else
        # Delegate everything else straight through
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

# Bash completion
_hop2_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local cmd="${COMP_WORDS[1]}"

    # Gather all available aliases
    local aliases
    aliases=$(sqlite3 ~/.hop2/hop2.db \
        "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null | tr '\n' ' ')

    case "$cmd" in
        rm|go)
            COMPREPLY=($(compgen -W "$aliases" -- "$cur"))
            ;;
        "")
            # First argument: can be any subcommand or alias
            local commands="add cmd list rm go"
            COMPREPLY=($(compgen -W "$commands $aliases" -- "$cur"))
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
        all_aliases=(${(f)"$(sqlite3 ~/.hop2/hop2.db \
            "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null)"})
        _arguments "1:command:(add cmd list rm go $all_aliases)"
    }
    compdef _hop2 hop2 h2 h
fi
