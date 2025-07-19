#!/bin/bash
# hop2 shell integration
# Add this to your ~/.bashrc or ~/.zshrc:
# source ~/.hop2/init.sh

# Main hop2 function that handles directory changes and command shortcuts
hop2() {
    # For multi-arg commands (add, cmd, rm), pass through directly
    if [ "$1" = "add" ] || [ "$1" = "cmd" ] || [ "$1" = "rm" ] || [ "$1" = "list" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ] || [ "$1" = "update-me" ] || [ "$1" = "uninstall-me" ]; then
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

# Rest of the file stays the same...