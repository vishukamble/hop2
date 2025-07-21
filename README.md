![hop2](https://raw.githubusercontent.com/vishukamble/hop2/main/assets/logos/hop2-logo-wide.svg)

**Stop navigating. Start hopping.**

A blazingly fast terminal navigator and command aliasing tool, built with Python. `hop2` is designed to be simple, fast, and dependency-free, helping you move around your filesystem and run common commands instantly.

[![hop2 Demo Video](https://github.com/vishukamble/hop2/releases/download/v1.0.0/hop2_screen.png)](https://github.com/vishukamble/hop2/releases/download/v1.0.0/demo_video.mp4)

[**hop2.tech**](https://hop2.tech)

[![Build Status](https://img.shields.io/github/actions/workflow/status/vishukamble/hop2/ci.yml?branch=main&label=build&logo=github)](https://github.com/vishukamble/hop2/actions)
[![GitHub Stars](https://img.shields.io/github/stars/vishukamble/hop2?style=social)](https://github.com/vishukamble/hop2)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)


---

## Features

-   **📁 Directory Shortcuts:** Save any directory with a short alias and hop to it from anywhere.
-   **⚡ Command Aliases:** Create powerful shortcuts for long, complex commands.
-   **🚀 Blazingly Fast:** Written in Python with a lightweight SQLite database for instant lookups.
-   **✨ Zero Dependencies:** Works out-of-the-box with just Python 3.
-   **🐧 Simple & Predictable:** No fuzzy matching or AI. Just simple, explicit aliases that work every time.
-   **🐚 Multi-Shell Support:** Works seamlessly with `bash` and `zsh`.

---

## 🚀 Installation

Installation is a single command. The script will automatically detect your shell and set everything up.

```bash
curl -sL install.hop2.tech | bash
```

After the installation, you just need to **reload your shell** for the changes to take effect:

```bash
# For Bash
source ~/.bashrc

# For Zsh
source ~/.zshrc
```

---

## 📖 Usage Guide

``` Directory Shortcuts

The core of `hop2` is making directory navigation instant.

```bash
# Go to a deep directory and save it with an alias
cd ~/work/projects/backend/api/controllers
hop2 add controllers

# Go to another project
cd ~/work/dev/company/products/web/frontend/src/components/shared/buttons
hop2 add buttons

# Now, from anywhere, hop back instantly using the 'h' command
cd ~
h controllers  # You are now in the backend controllers directory
h buttons      # You are now in the frontend buttons directory
```

``` Command Shortcuts

Stop typing long commands over and over.

```bash
# Create an alias for a complex git log command
hop2 cmd glog "git log --oneline --graph --all --decorate"

# Use it anywhere
h my-project-repo
hop2 glog

# Create an alias to find the 10 largest files
hop2 cmd bigfiles "find . -type f -printf '%s %p\n' | sort -nr | head -n 10"
hop2 bigfiles
```

``` Managing Your Shortcuts

-   **List all shortcuts:** See everything you've saved with a clean, formatted table.
    ```bash
    hop2 list
    ```
-   **Remove a shortcut:**
    ```bash
    hop2 rm buttons
    ```

``` Updating & Uninstalling

-   **Update to the latest version:**
    ```bash
    hop2 --update
    ```
-   **Uninstall `hop2` completely:** This removes the executable, all data, and cleans up your shell configuration file automatically.
    ```bash
    hop2 --uninstall
    ```

---

## Contributing

We love PRs and suggestions! This project is intentionally kept simple. Good first issues include bug fixes, documentation improvements, or adding support for other shells like `fish`.

## License

This project is licensed under the **MIT License**.