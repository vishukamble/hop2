#!/bin/bash
# hop2 installer script
set -e

# --- HEADER ---
cat <<'EOF'
                      .--.
                     |o_o |
                     |:_/ |
                `~   //   \ \   ~'
                 ~  (|     | )  ~
               .~` /'\_   _/`\ `~.
              /   \___)=(___/   \

   /-----------------\               /------------------\
  <   HOP FROM...   >             <   ...TO HERE!    >
   \_________________/               \______HOP2_______/
~~~~~~~~~~~~~~~~~~~~~~~~~~         ~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF
# ---
echo "Installing hop2..."

# 1) Ensure Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed." >&2
    exit 1
fi

# 2) Pick install directory
INSTALL_DIR=""
if [ -d "$HOME/.local/bin" ] && [ -w "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
elif [ -d "$HOME/bin" ] && [ -w "$HOME/bin" ]; then
    INSTALL_DIR="$HOME/bin"
elif [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
fi

if [ -z "$INSTALL_DIR" ]; then
    echo "❌ Error: Could not find a writable directory in PATH. Please create one (e.g., mkdir -p ~/.local/bin) and add it to your PATH." >&2
    exit 1
fi
mkdir -p "$INSTALL_DIR"


# --- THIS IS THE CORRECTED LOGIC ---
# 3) Detect the user's default shell to find the correct RC file
if [[ "$SHELL" == *"zsh"* ]]; then
    RC_FILE="$HOME/.zshrc"
    PROFILE_FILE="$HOME/.zprofile"
else
    # Default to .bashrc for bash or any other shell
    RC_FILE="$HOME/.bashrc"
    PROFILE_FILE="$HOME/.bash_profile"
fi
# ---

# 4) Prepare the ~/.hop2 directory and download files
echo "✔️  Preparing environment in ~/.hop2"
mkdir -p "$HOME/.hop2"

echo "📥  Downloading hop2 core scripts..."
# Use a temporary file for safety
TMP_HOP2=$(mktemp)
TMP_INIT=$(mktemp)
if command -v curl &> /dev/null; then
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/hop2.py -o "$TMP_HOP2"
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/init.sh -o "$TMP_INIT"
else
    echo "❌ Error: curl is required for installation." >&2
    exit 1
fi

# 5) Install the hop2 binary and init script
chmod +x "$TMP_HOP2"
mv "$TMP_HOP2" "$INSTALL_DIR/hop2"
mv "$TMP_INIT" "$HOME/.hop2/init.sh"
echo "✅  hop2 installed successfully to $INSTALL_DIR/hop2"

# 6) Ensure shell integration is sourced in the correct file
SOURCE_LINE="source ~/.hop2/init.sh"
if ! grep -q "$SOURCE_LINE" "$RC_FILE"; then
    echo "➕  Adding hop2 to your shell startup file ($RC_FILE)"
    echo -e "\n# hop2 shell integration\n$SOURCE_LINE" >> "$RC_FILE"
fi

# Also add to profile file for Zsh login shells on some systems (like macOS)
if [[ "$SHELL" == *"zsh"* ]] && [ -f "$PROFILE_FILE" ] && ! grep -q "$SOURCE_LINE" "$PROFILE_FILE"; then
    echo "➕  Adding hop2 to $PROFILE_FILE for compatibility"
    echo -e "\n# hop2 shell integration\n$SOURCE_LINE" >> "$PROFILE_FILE"
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
│ h work                           │ Use "h" for even shorter directory jumps │
└──────────────────────────────────┴──────────────────────────────────────────┘

⚠️  Final Step: Reload your shell to complete the installation!

    source ~/.bashrc   (or source ~/.zshrc)

To remove hop2 later, just run: hop2 --uninstall
EOF