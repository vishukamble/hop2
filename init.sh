#!/bin/bash
# hop2 shell integration
# Add this to your ~/.bashrc or ~/.zshrc:
# source ~/.hop2/init.sh

# Main hop2 function that handles directory changes and command shortcuts
hop2() {
    # Don't do anything if no arguments are provided
    if [ "$#" -eq 0 ]; then
        command hop2 --help
        return
    fi

    local output
    # If the user asked to uninstall or update, run hop2 directly (no capture),
    # so prompts and input() work as expected:
    if [ "$1" = "--uninstall" ] || [ "$1" = "--update" ] ; then
        command hop2 "$@"
        return $?
    fi

    # Otherwise capture output so we can intercept __HOP2_CD:… sequences
    output=$(command hop2 "$@")
    exit_code=$?

    # Check if the python script gave us the magic string to change directory
    if [[ $output == __HOP2_CD:* ]]; then
        local path="${output#__HOP2_CD:}"
        cd "$path" || return 1
    elif [ $exit_code -ne 0 ]; then
        # If the script failed, print its output (which is the error message)
        # to stderr and preserve the exit code.
        echo "$output" >&2
        return $exit_code
    elif [ -n "$output" ];then
        # If the script succeeded and printed something, show it.
        # This is for commands like 'hop2 gs' which print "→ Running...".
        echo "$output"
    fi
}

# Shorter alias 'h' for jumping (or listing)
h() {
    # If no arguments are given, run the list command
    if [ -z "$1" ]; then
        hop2 list
    else
        # Otherwise, pass ALL arguments to the main hop2 function
        hop2 "$@"
    fi
}

# Bash completion with ALL commands
if [ -n "$BASH_VERSION" ]; then
    _hop2_completion() {
      local cur prev commands aliases
      cur="${COMP_WORDS[COMP_CWORD]}"
      prev="${COMP_WORDS[COMP_CWORD-1]}"

      if (( COMP_CWORD == 1 )); then
        commands="add cmd list ls rm go --update --uninstall --help"
        aliases=$(sqlite3 ~/.hop2/hop2.db \
          "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null \
           | tr '\n' ' ')
        COMPREPLY=( $(compgen -W "$commands $aliases" -- "$cur") )
        return
      fi

      case "$prev" in
        rm|go)
          aliases=$(sqlite3 ~/.hop2/hop2.db \
            "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null \
             | tr '\n' ' ')
          COMPREPLY=( $(compgen -W "$aliases" -- "$cur") );;
      esac
    }

    complete -F _hop2_completion hop2
    complete -F _hop2_completion h2
    complete -F _hop2_completion h
fi

# Zsh completion
if [ -n "$ZSH_VERSION" ]; then
    # First ensure the completion system is loaded
    if ! type compdef &>/dev/null; then
        autoload -Uz compinit && compinit
    fi

    _hop2() {
        local -a all_aliases
        all_aliases=(${(f)"$(sqlite3 ~/.hop2/hop2.db 'SELECT alias FROM directories UNION SELECT alias FROM commands' 2>/dev/null)"})
        _arguments "1:command:(add cmd list ls rm $all_aliases)"
    }

    # Only set up completion if compdef is available
    if type compdef &>/dev/null; then
        compdef _hop2 hop2 h2 h
    fi
fi