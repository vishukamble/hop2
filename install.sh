#!/usr/bin/env bash
# hop2 installer script

set -Eeuo pipefail

TMP_HOP2=""
TMP_INIT=""

cleanup() {
  [ -n "${TMP_HOP2:-}" ] && [ -f "$TMP_HOP2" ] && rm -f "$TMP_HOP2"
  [ -n "${TMP_INIT:-}" ] && [ -f "$TMP_INIT" ] && rm -f "$TMP_INIT"
}
trap cleanup EXIT

# --- HEADER ---
cat <<'EOF'
         (\_/)           HOP2 Installer
         ( •_•)  /-----------------\     /------------------\
        / >💲  <   HOP FROM...   >   <   ...TO HERE!    >
                 \_________________/     \______HOP2_______/
EOF
echo "Installing hop2..."

# 1) Ensure Python 3 is available
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Error: Python 3 is required but not installed." >&2
  exit 1
fi

# Ensure curl is available
if ! command -v curl >/dev/null 2>&1; then
  echo "❌ Error: curl is required for installation." >&2
  exit 1
fi

# 2) Pick install directory
INSTALL_DIR=""
if [ -d "$HOME/.local/bin" ] && [ -w "$HOME/.local/bin" ]; then
  INSTALL_DIR="$HOME/.local/bin"
elif [ -d "$HOME/bin" ] && [ -w "$HOME/bin" ]; then
  INSTALL_DIR="$HOME/bin"
elif [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
  INSTALL_DIR="/usr/local/bin"
fi

if [ -z "$INSTALL_DIR" ]; then
  echo "❌ Error: Could not find a writable directory in PATH." >&2
  echo "   Create one (e.g., mkdir -p ~/.local/bin) and add it to PATH." >&2
  exit 1
fi
mkdir -p "$INSTALL_DIR"

# Warn if install dir is not on PATH
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "⚠️  Warning: $INSTALL_DIR is not in your PATH."
    echo "   Add this to your shell config:"
    echo "   export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac

# 3) Detect shell and RC file
if [[ "${SHELL:-}" == *"zsh"* ]]; then
  RC_FILE="$HOME/.zshrc"
  PROFILE_FILE="$HOME/.zprofile"
  RELOAD_CMD="source ~/.zshrc"
else
  RC_FILE="$HOME/.bashrc"
  PROFILE_FILE="$HOME/.bash_profile"
  RELOAD_CMD="source ~/.bashrc"
fi

# 4) Prepare ~/.hop2 and download files
echo "✔️  Preparing environment in ~/.hop2"
mkdir -p "$HOME/.hop2"

echo "📥  Downloading hop2 core scripts..."
TMP_HOP2="$(mktemp)"
TMP_INIT="$(mktemp)"

curl -fsSL --retry 3 --retry-delay 1 --connect-timeout 10 \
  "https://raw.githubusercontent.com/vishukamble/hop2/main/hop2.py" \
  -o "$TMP_HOP2"

curl -fsSL --retry 3 --retry-delay 1 --connect-timeout 10 \
  "https://raw.githubusercontent.com/vishukamble/hop2/main/init.sh" \
  -o "$TMP_INIT"

# Basic integrity sanity checks
if ! head -n 1 "$TMP_HOP2" | grep -q '^#!/usr/bin/env python3'; then
  echo "❌ Error: downloaded hop2.py looks invalid." >&2
  exit 1
fi

if ! head -n 1 "$TMP_INIT" | grep -q '^#!/bin/bash'; then
  echo "❌ Error: downloaded init.sh looks invalid." >&2
  exit 1
fi

# 5) Install hop2 binary and init script
chmod +x "$TMP_HOP2"
mv "$TMP_HOP2" "$INSTALL_DIR/hop2"
mv "$TMP_INIT" "$HOME/.hop2/init.sh"
echo "✅  hop2 installed successfully to $INSTALL_DIR/hop2"

# 6) Ensure shell integration is sourced
touch "$RC_FILE"
if [[ "${SHELL:-}" == *"zsh"* ]]; then
  touch "$PROFILE_FILE"
fi

SOURCE_LINE='source ~/.hop2/init.sh'

if ! grep -Fqx "$SOURCE_LINE" "$RC_FILE"; then
  echo "➕  Adding hop2 to your shell startup file ($RC_FILE)"
  printf "\n# hop2 shell integration\n%s\n" "$SOURCE_LINE" >> "$RC_FILE"
fi

# For zsh login shells on some systems (like macOS)
if [[ "${SHELL:-}" == *"zsh"* ]] && ! grep -Fqx "$SOURCE_LINE" "$PROFILE_FILE"; then
  echo "➕  Adding hop2 to $PROFILE_FILE for compatibility"
  printf "\n# hop2 shell integration\n%s\n" "$SOURCE_LINE" >> "$PROFILE_FILE"
fi

# --- FOOTER ---
cat <<'EOF'

🚀 Quick Start
┌──────────────────────────────────┬──────────────────────────────────────────┐
│ Command                          │ What it does                             │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ hop2 add work                    │ Add current directory as "work"          │
│ hop2 work                        │ Jump to that directory                   │
│ hop2 cmd gs 'git status'         │ Create command alias "gs"                │
│ hop2 gs                          │ Run "git status"                         │
│ h / hop / h2 work                │ Short jump (auto-selected if h is taken) │
│ hop2 --backup                    │ Backup shortcuts to timestamped JSON     │
│ hop2 --restore backup.json       │ Restore shortcuts from backup file       │
└──────────────────────────────────┴──────────────────────────────────────────┘

Note: hop2 auto-selects your short command as: h, or hop, or h2.
EOF

echo ""
echo "⚠️  Final Step: Reload your shell to complete the installation!"
echo ""
echo "    $RELOAD_CMD"
echo ""
echo "To remove hop2 later, just run: hop2 --uninstall"
