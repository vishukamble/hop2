#!/bin/bash
# hop2 uninstaller

echo "Uninstalling hop2..."

# Remove executables from possible locations
for dir in /usr/local/bin ~/.local/bin ~/bin; do
    [ -f "$dir/hop2" ] && rm -f "$dir/hop2" && echo "✓ Removed hop2 from $dir"
done

# Remove hop2 directory
[ -d ~/.hop2 ] && rm -rf ~/.hop2 && echo "✓ Removed ~/.hop2 directory"

# Remove from shell configs
for rc in ~/.bashrc ~/.zshrc; do
    if [ -f "$rc" ]; then
        sed -i '/source.*\.hop2.*init\.sh/d' "$rc" && echo "✓ Removed from $rc"
    fi
done

echo "✓ hop2 uninstalled successfully"
echo "Please reload your shell: source ~/.bashrc"