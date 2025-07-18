#!/bin/bash
# hop2 shell integration
# Add this to your ~/.bashrc or ~/.zshrc:
# source /path/to/hop2.sh

# Main hop2 function that handles directory changes
hop2() {
    if [ "$1" = "go" ] || [ "$1" = "" ]; then
        # If using 'go' command or just an alias, we need to cd
        local output
        output=$(command hop2 "$@" 2>&1)

        if [[ $output == __HOP2_CD:* ]]; then
            # Extract path and cd to it
            local path="${output#__HOP2_CD:}"
            cd "$path" || return 1
        else
            # Not a cd command, just print output
            echo "$output"
        fi
    else
        # For all other commands, run hop2 normally
        command hop2 "$@"
    fi
}

# Shorter alias
alias h2="hop2"

# Even shorter function for jumping to directories
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

    # Get all aliases from database
    local aliases=$(sqlite3 ~/.hop2/hop2.db "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null | tr '\n' ' ')

    case "$cmd" in
        rm|go)
            COMPREPLY=($(compgen -W "$aliases" -- "$cur"))
            ;;
        "")
            # First argument - could be a command or an alias
            local commands="add cmd list rm go"
            COMPREPLY=($(compgen -W "$commands $aliases" -- "$cur"))
            ;;
    esac
}

# Enable completion for bash
if [ -n "$BASH_VERSION" ]; then
    complete -F _hop2_completion hop2
    complete -F _hop2_completion h2
    complete -F _hop2_completion h
fi

# ZSH completion (basic)
if [ -n "$ZSH_VERSION" ]; then
    _hop2() {
        local -a aliases
        aliases=(${(f)"$(sqlite3 ~/.hop2/hop2.db "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null)"})
        _arguments "1:command:(add cmd list rm go $aliases)"
    }
    compdef _hop2 hop2
    compdef _hop2 h2
    compdef _hop2 h
fi