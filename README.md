![hop2](assets/logos/hop2-logo-wide.svg)

# hop2 🚀

Quick directory jumping and command aliasing for your terminal. Like `z` or `autojump`, but simpler.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/vishukamble/hop2/ci.yml?branch=main&label=build&logo=github)](https://github.com/vishukamble/hop2/actions)

---

## Table of Contents

- [Why hop2?](#why-hop2)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Directory Shortcuts](#directory-shortcuts)
  - [Command Shortcuts](#command-shortcuts)
- [Real-world Examples](#real-world-examples)
- [Tips & Gotchas](#tips--gotchas)
- [PowerShell Support (Coming Soon)](#powershell-support-coming-soon)
- [Contributing](#contributing)
- [License](#license)

---

## Why hop2?

Ever been 6 folders deep and need to jump somewhere else? Or tired of typing long commands over and over?

\`\`\`bash
# Instead of: cd ../../../../../other-project/src
hop2 src

# Instead of: kubectl delete pod my-pod-name
hop2 kdp my-pod-name
\`\`\`

---

## Features

- **Directory shortcuts**: Jump to any directory from anywhere
- **Command aliases**: Create shortcuts for long commands
- **Zero dependencies**: Just Python 3 and SQLite
- **Shell integration**: Works with bash & zsh (PowerShell coming soon)
- **Simple**: No AI, no fuzzy matching—just aliases you control

---

## Installation

\`\`\`bash
# 1. Install hop2
curl -sL [https://raw.githubusercontent.com/vishukamble/hop2/main/install.sh](https://raw.githubusercontent.com/vishukamble/hop2/main/install.sh) | bash

# 2. Enable shell integration
echo 'source ~/.hop2/hop2.sh' >> ~/.bashrc   # or ~/.zshrc
source ~/.bashrc
\`\`\`

---

## Usage

### Directory Shortcuts

\`\`\`bash
# Add current directory with an alias
hop2 add project

# Add specific directory
hop2 add docs ~/Documents/important-docs

# Jump to a directory (from anywhere!)
hop2 project
# or even shorter:
h project

# List all shortcuts
hop2 list
\`\`\`

### Command Shortcuts

\`\`\`bash
# Create a command alias
hop2 cmd kdp "kubectl delete pod"
hop2 cmd gs "git status"
hop2 cmd build "npm run build && npm test"

# Use it
hop2 kdp my-pod-name
hop2 gs
hop2 build
\`\`\`

---

## Real-world Examples

\`\`\`bash
# Save your most-used workspaces
cd ~/work/frontend/src/components
hop2 add frontend

cd ~/work/backend/api/handlers
hop2 add backend

cd ~/work/infrastructure/kubernetes
hop2 add k8s

# Now hop around instantly:
h frontend   # you’re in frontend components
h backend    # you’re in backend handlers
h k8s        # you’re in kubernetes configs

# Common commands
hop2 cmd dc "docker-compose"
hop2 cmd k "kubectl"
hop2 cmd tf "terraform"

hop2 dc up -d
hop2 k get pods
hop2 tf plan
\`\`\`

---

## Tips & Gotchas

- **Unique aliases**: Directory and command aliases share the same namespace.
- **Backup & restore**: Your shortcuts live in `~/.hop2/hop2.db`. Back it up to migrate.
- **Security**: Command aliases run exactly what you type—avoid untrusted inputs.

---

## PowerShell Support (Coming Soon)

\`\`\`powershell
# In your PowerShell profile:
# Add support so that `hop2 project` does the same cd behavior.
\`\`\`

---

## Contributing

We love PRs! Good first issues:

- Bug fixes & docs improvements
- PowerShell integration
- Enhanced shell completions

Please avoid:

- External dependencies
- Fuzzy-matching features (other tools excel at that)
- Over-engineering the core simplicity

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

Because sometimes you just want to `hop2` where you’re going.
```