#!/bin/bash
# hop2 installer script
set -e

# ——— HEADER (Penguin Hop) ————————————————————————————————————————
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
# ——————————————————————————————————————————————————————————————————
echo "Installing hop2..."

# (The rest of the script is the same)
# 1) Ensure Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed." >&2
    exit 1
fi

# 2) Pick install directory
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -d "$HOME/.local/bin" ] && [ -w "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
else
    INSTALL_DIR="$HOME/bin"
    mkdir -p "$INSTALL_DIR"
fi

# 3) Detect RC file
if [ -n "$ZSH_VERSION" ]; then
    HOP2_RC="$HOME/.zshrc"
else
    HOP2_RC="$HOME/.bashrc" # Default to bashrc
fi

# 4) Prepare the ~/.hop2 directory and download files
echo "✔️  Preparing environment in ~/.hop2"
mkdir -p "$HOME/.hop2"

echo "📥  Downloading hop2 core scripts..."
if command -v curl &> /dev/null; then
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/hop2.py -o /tmp/hop2
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/init.sh -o "$HOME/.hop2/init.sh"
else
    echo "Error: curl is required for installation." >&2
    exit 1
fi

# 5) Install the hop2 binary
chmod +x /tmp/hop2
mv /tmp/hop2 "$INSTALL_DIR/hop2"
echo "✅  hop2 installed successfully to $INSTALL_DIR/hop2"

# 6) Ensure shell integration is sourced
if ! grep -q "source ~/.hop2/init.sh" "$HOP2_RC"; then
    echo "➕  Adding hop2 to your shell startup file ($HOP2_RC)"
    echo -e "\n# hop2 shell integration\nsource ~/.hop2/init.sh" >> "$HOP2_RC"
fi

# ——— FOOTER ——————————————————————————————————————————————————————
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
# ——————————————————————————————————————————————————————————————————