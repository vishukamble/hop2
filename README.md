# hop2 🚀

Quick directory jumping and command aliasing for your terminal. Like `z` or `autojump`, but simpler.

## Why hop2?

Ever been 6 folders deep and need to jump somewhere else? Or tired of typing long commands?

```bash
# Instead of: cd ../../../../../other-project/src
hop2 src

# Instead of: kubectl delete pod my-pod-name
hop2 kdp my-pod-name
```

## Features

- **Directory shortcuts**: Jump to any directory from anywhere
- **Command aliases**: Create shortcuts for long commands
- **Zero dependencies**: Just Python 3 and SQLite
- **Shell integration**: Works with bash, zsh (PowerShell coming soon)
- **Simple**: No AI, no fuzzy matching, just simple aliases you control

## Installation

```bash
# 1. Install hop2
curl -sL https://raw.githubusercontent.com/YOUR_USERNAME/hop2/main/install.sh | bash

# 2. Add to your shell (.bashrc or .zshrc)
echo 'source ~/.hop2/hop2.sh' >> ~/.bashrc
source ~/.bashrc
```

## Usage

### Directory Shortcuts

```bash
# Add current directory with an alias
hop2 add project

# Add specific directory
hop2 add docs ~/Documents/important-docs

# Jump to directory (from anywhere!)
hop2 project
# or even shorter
h project

# List all shortcuts
hop2 list
```

### Command Shortcuts

```bash
# Create command alias
hop2 cmd kdp "kubectl delete pod"
hop2 cmd gs "git status"
hop2 cmd build "npm run build && npm test"

# Use it
hop2 kdp my-pod-name
hop2 gs
hop2 build
```

### Real-world Examples

```bash
# Working on multiple projects
cd ~/work/frontend/src/components
hop2 add frontend

cd ~/work/backend/api/handlers  
hop2 add backend

cd ~/work/infrastructure/kubernetes
hop2 add k8s

# Now jump around
h frontend  # you're in frontend components
h backend   # you're in backend handlers
h k8s       # you're in kubernetes configs

# Common commands
hop2 cmd dc "docker-compose"
hop2 cmd k "kubectl"
hop2 cmd tf "terraform"

hop2 dc up -d
hop2 k get pods
hop2 tf plan
```

## Tips

- Use short, memorable aliases
- `h` is aliased to `hop2` for even quicker access
- Your most-used shortcuts appear first in listings
- Shortcuts are stored in `~/.hop2/hop2.db`

## PowerShell Support (Coming Soon)

```powershell
# Future support
hop2 add project
hop2 project  # Will work in PowerShell too
```

## Contributing

Keep it simple. PRs welcome for:
- Bug fixes  
- PowerShell support
- Better shell completions
- Documentation

Please no:
- External dependencies
- Fuzzy matching (there are other tools for that)
- Complex features

## License

MIT

---

Because sometimes you just want to `hop2` where you're going.