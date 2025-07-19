#!/bin/bash
# hop2 shell integration
# Add this to your ~/.bashrc or ~/.zshrc:
#   source ~/.hop2/init.sh

set -e

echo "Installing hop2..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Determine where to install the `hop2` executable
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
elif [ -w "$HOME/.local/bin" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
else
    INSTALL_DIR="$HOME/bin"
    mkdir -p "$INSTALL_DIR"
fi

# Prepare .hop2 directory
mkdir -p "$HOME/.hop2"

echo "Downloading hop2 core..."
# Download hop2.py and init.sh (renamed from init.sh)
if command -v curl &> /dev/null; then
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/hop2.py -o /tmp/hop2
    curl -sL https://raw.githubusercontent.com/vishukamble/hop2/main/init.sh -o "$HOME/.hop2/init.sh"
elif command -v wget &> /dev/null; then
    wget -q https://raw.githubusercontent.com/vishukamble/hop2/main/hop2.py -O /tmp/hop2
    wget -q https://raw.githubusercontent.com/vishukamble/hop2/main/init.sh -O "$HOME/.hop2/init.sh"
else
    echo "Error: curl or wget is required for installation."
    exit 1
fi

# Install the hop2 executable
chmod +x /tmp/hop2
mv /tmp/hop2 "$INSTALL_DIR/hop2"

# Make the shell integration script executable
chmod +x "$HOME/.hop2/init.sh"

echo "✓ hop2 installed successfully to $INSTALL_DIR/hop2"
echo

# Detect user shell and recommend sourcing
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

cat <<EOF
To enable directory jumping, add this line to $SHELL_RC:

    source ~/.hop2/init.sh

Then reload your shell:

    source $SHELL_RC

Quick start:
  hop2 add work            # Add current directory as 'work'
  hop2 work                # Jump to that directory

  hop2 cmd gs 'git status' # Create command alias 'gs'
  hop2 gs                  # Run git status

  h work                   # Even shorter: use 'h' to jump

For more info: hop2 --help
EOF