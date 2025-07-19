#!/bin/bash
# hop2 installer script
# ——————————————————————————————————————————————
# Add this to your ~/.bashrc or ~/.zshrc:
#   source ~/.hop2/init.sh
# ——————————————————————————————————————————————

set -e

echo "Installing hop2..."

# 1) Ensure Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# 2) Pick install directory for the `hop2` executable
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -w "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
else
    INSTALL_DIR="$HOME/bin"
    mkdir -p "$INSTALL_DIR"
fi

# 3) Detect which shell RC file to update
if [ -n "$ZSH_VERSION" ]; then
    HOP2_RC=".zshrc"
elif [ -n "$BASH_VERSION" ]; then
    HOP2_RC=".bashrc"
else
    HOP2_RC=".bashrc"  # fallback
fi

echo "✔️ Will add “source ~/.hop2/init.sh” to ~/$HOP2_RC"

# 4) Prepare the ~/.hop2 directory
mkdir -p "$HOME/.hop2"

echo "Downloading hop2 core..."
if command -v curl &> /dev/null; then
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/hop2.py   -o /tmp/hop2
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/init.sh  -o "$HOME/.hop2/init.sh"
elif command -v wget &> /dev/null; then
    wget -q https://raw.githubusercontent.com/vishukamble/hop2/main/hop2.py   -O /tmp/hop2
    wget -q https://raw.githubusercontent.com/vishukamble/hop2/main/init.sh  -O "$HOME/.hop2/init.sh"
else
    echo "Error: curl or wget is required for installation."
    exit 1
fi

# 5) Install the `hop2` binary
chmod +x /tmp/hop2
mv /tmp/hop2 "$INSTALL_DIR/hop2"

# 6) Make the shell integration script executable
chmod +x "$HOME/.hop2/init.sh"

echo "✓ hop2 installed successfully to $INSTALL_DIR/hop2"
echo

# 7) Print out the “source” instructions in a standout box
cat <<EOF
------------------------------------------------------------
⚠️  Important: you must source the integration script
------------------------------------------------------------

Add this line to ~/$HOP2_RC (if you haven't already):

    source ~/.hop2/init.sh

Then reload your shell:

    source ~/$HOP2_RC

✅ Quick start
| Command                         | What it does                           |
|---------------------------------|----------------------------------------|
| hop2 add work                   | Add current directory as “work”        |
| hop2 work                       | Jump to that directory                 |
| hop2 cmd gs 'git status'        | Create command alias “gs”              |
| hop2 gs                         | Run “git status”                       |
| h work                          | Even shorter: use “h” to jump          |

For full usage, run:

    hop2 --help

Enjoy hopping! 🚀
------------------------------------------------------------
EOF