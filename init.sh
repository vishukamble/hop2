#!/bin/bash
# hop2 shell integration
# Source from ~/.bashrc or ~/.zshrc:
#   source ~/.hop2/init.sh

# -----------------------------------------------------------------------------
# Choose short command safely:
# - If user pre-sets HOP2_SHORTCUT to one of: h, hop, h2 -> honor it
# - Else auto-pick first available: h -> hop -> h2
# -----------------------------------------------------------------------------

case "${HOP2_SHORTCUT:-}" in
  h|hop|h2) ;;
  *) unset HOP2_SHORTCUT ;;
esac

if [ -z "${HOP2_SHORTCUT:-}" ]; then
  if command -v h >/dev/null 2>&1; then
    if command -v hop >/dev/null 2>&1; then
      HOP2_SHORTCUT="h2"
    else
      HOP2_SHORTCUT="hop"
    fi
  else
    HOP2_SHORTCUT="h"
  fi
fi

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

# Return codes:
#   0 => alias exists in directories table (dir shortcut)
#   1 => alias does not exist in directories table
#   2 => unknown (sqlite3/db unavailable)
_hop2_is_dir_alias() {
  local alias="$1"
  local db="$HOME/.hop2/hop2.db"

  if ! command -v sqlite3 >/dev/null 2>&1; then
    return 2
  fi
  if [ ! -f "$db" ]; then
    return 2
  fi

  local exists
  exists="$(sqlite3 "$db" "SELECT 1 FROM directories WHERE alias='${alias//\'/''}' LIMIT 1;" 2>/dev/null)"
  if [ "$exists" = "1" ]; then
    return 0
  fi
  return 1
}

# Execute hop2 and capture output so we can intercept __HOP2_CD:...
_hop2_run_capture_for_cd() {
  local output exit_code path

  output="$(command hop2 "$@")"
  exit_code=$?

  if [[ "$output" == __HOP2_CD:* ]]; then
    path="${output#__HOP2_CD:}"
    cd "$path" || return 1
    return 0
  fi

  if [ $exit_code -ne 0 ]; then
    [ -n "$output" ] && echo "$output" >&2
    return $exit_code
  fi

  [ -n "$output" ] && echo "$output"
  return 0
}

# Shared behavior for short command wrapper
_hop2_shortcut() {
  if [ "$#" -eq 0 ]; then
    hop2 list
  else
    hop2 "$@"
  fi
}

# -----------------------------------------------------------------------------
# Main hop2 shell function
# -----------------------------------------------------------------------------
hop2() {
  # No args -> help
  if [ "$#" -eq 0 ]; then
    command hop2 --help
    return
  fi

  local first="$1"

  # Direct pass-through for interactive/global flags
  case "$first" in
    --uninstall|--update|--backup|--restore|--help|-h)
      command hop2 "$@"
      return $?
      ;;
  esac

  # Direct pass-through for known subcommands (no need to capture output)
  case "$first" in
    add|cmd|list|ls|rm|update)
      command hop2 "$@"
      return $?
      ;;
  esac

  # For potential aliases:
  # - If directory alias: capture and intercept __HOP2_CD
  # - If command alias / unknown alias: run directly (streams output naturally)
  _hop2_is_dir_alias "$first"
  case $? in
    0)
      _hop2_run_capture_for_cd "$@"
      return $?
      ;;
    1)
      command hop2 "$@"
      return $?
      ;;
    2)
      # Fallback: unknown detection state; capture to preserve directory jumping
      _hop2_run_capture_for_cd "$@"
      return $?
      ;;
  esac
}

# -----------------------------------------------------------------------------
# Define selected short command
# -----------------------------------------------------------------------------
case "$HOP2_SHORTCUT" in
  h)   h()   { _hop2_shortcut "$@"; } ;;
  hop) hop() { _hop2_shortcut "$@"; } ;;
  h2)  h2()  { _hop2_shortcut "$@"; } ;;
esac

# -----------------------------------------------------------------------------
# Bash completion
# -----------------------------------------------------------------------------
if [ -n "$BASH_VERSION" ]; then
  _hop2_completion() {
    local cur prev commands aliases
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    if (( COMP_CWORD == 1 )); then
      commands="add cmd list ls rm update --update --uninstall --backup --restore --help"

      aliases="$(sqlite3 ~/.hop2/hop2.db \
        "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null \
        | tr '\n' ' ')"

      COMPREPLY=( $(compgen -W "$commands $aliases" -- "$cur") )
      return
    fi

    case "$prev" in
      rm)
        aliases="$(sqlite3 ~/.hop2/hop2.db \
          "SELECT alias FROM directories UNION SELECT alias FROM commands" 2>/dev/null \
          | tr '\n' ' ')"
        COMPREPLY=( $(compgen -W "$aliases" -- "$cur") )
        ;;
      --restore)
        COMPREPLY=( $(compgen -f -- "$cur") )
        ;;
    esac
  }

  complete -F _hop2_completion hop2
  complete -F _hop2_completion "$HOP2_SHORTCUT"
fi

# -----------------------------------------------------------------------------
# Zsh completion
# -----------------------------------------------------------------------------
if [ -n "$ZSH_VERSION" ]; then
  if ! type compdef &>/dev/null; then
    autoload -Uz compinit && compinit
  fi

  _hop2() {
    local -a all_aliases
    all_aliases=(${(f)"$(sqlite3 ~/.hop2/hop2.db 'SELECT alias FROM directories UNION SELECT alias FROM commands' 2>/dev/null)"})
    _arguments "1:command:(add cmd list ls rm update --backup --restore --update --uninstall --help $all_aliases)"
  }

  if type compdef &>/dev/null; then
    compdef _hop2 hop2 "$HOP2_SHORTCUT"
  fi
fi
