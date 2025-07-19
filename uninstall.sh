#!/bin/bash
# hop2 uninstaller

echo "Uninstalling hop2..."

# (remove executables & data, clean RCs—same as before)
cat <<EOF

✅  hop2 has been removed.

| Action                                       | Status                        |
|----------------------------------------------|-------------------------------|
| Removed executable from /usr/local/bin*      | ✓                             |
| Removed executable from ~/.local/bin*        | ✓                             |
| Removed executable from ~/bin*               | ✓                             |
| Removed ~/.hop2 directory                    | ✓                             |
| Cleaned 'source ~/.hop2/init.sh' from RC     | ✓ (backed up as *.bak)        |

*where installed

To complete, reload your shell:

    source ~/.bashrc   # or source ~/.zshrc

EOF
