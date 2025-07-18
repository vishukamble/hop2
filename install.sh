#!/bin/bash
# hop2 installer script

set -e

echo "Installing hop2..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Determine install location
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -w "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
else
    INSTALL_DIR="$HOME/bin"
    mkdir -p "$INSTALL_DIR"
fi

# Create hop2 directory
mkdir -p ~/.hop2

# Download files
echo "Downloading hop2..."
if command -v curl &> /dev/null; then
    curl -sL https://raw.githubusercontent.com/YOUR_USERNAME/hop2/main/hop2.py -o /tmp/hop2
    curl -sL https://raw.githubusercontent.com/YOUR_USERNAME/hop2/main/hop2.sh -o ~/.hop2/hop2.sh
elif command -v wget &> /dev/null; then
    wget -q https://raw.githubusercontent.com/YOUR_USERNAME/hop2/main/hop2.py -O /tmp/hop2
    wget -q https://raw.githubusercontent.com/YOUR_USERNAME/hop2/main/hop2.sh -O ~/.hop2/hop2.sh
else
    echo "Error: curl or wget is required for installation"
    exit 1
fi

# Make executable and move to install directory
chmod +x /tmp/hop2
mv /tmp/hop2 "$INSTALL_DIR/hop2"
chmod +x ~/.hop2/hop2.sh

echo "✓ hop2 installed successfully to $INSTALL_DIR/hop2"
echo ""

# Detect shell and provide instructions
if [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
    SHELL_NAME="bash"
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
    SHELL_NAME="zsh"
else
    SHELL_RC="your shell's RC file"
    SHELL_NAME="your shell"
fi

echo "⚠️  To enable directory jumping, add this line to $SHELL_RC:"
echo ""
echo "    source ~/.hop2/hop2.sh"
echo ""
echo "Then reload your shell:"
echo "    source $SHELL_RC"
echo ""
echo "Quick start:"
echo "  hop2 add work ~/work     # Add a directory shortcut"
echo "  hop2 work                # Jump to that directory"
echo "  hop2 cmd gs 'git status' # Add a command shortcut"
echo "  hop2 gs                  # Run that command"
echo ""
echo "For more info: hop2 --help"