#!/usr/bin/env python3
"""
hop2 - Quick directory and command aliasing for the terminal
"""
import os
import sys
import sqlite3
import subprocess
import argparse
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

# Config
DB_PATH = os.path.expanduser("~/.hop2/hop2.db")
DB_DIR = os.path.dirname(DB_PATH)


def init_db():
    """Initialize the database"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Table for directory shortcuts
    c.execute('''CREATE TABLE IF NOT EXISTS directories
                 (
                     alias
                     TEXT
                     PRIMARY
                     KEY,
                     path
                     TEXT
                     NOT
                     NULL,
                     created_at
                     TIMESTAMP,
                     uses
                     INTEGER
                     DEFAULT
                     0
                 )''')

    # Table for command shortcuts
    c.execute('''CREATE TABLE IF NOT EXISTS commands
                 (
                     alias
                     TEXT
                     PRIMARY
                     KEY,
                     command
                     TEXT
                     NOT
                     NULL,
                     created_at
                     TIMESTAMP,
                     uses
                     INTEGER
                     DEFAULT
                     0
                 )''')

    conn.commit()
    conn.close()


def add_directory(alias, path=None):
    """Add a directory shortcut"""
    if path is None:
        path = os.getcwd()
    else:
        path = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(path):
        print(f"✗ Path does not exist: {path}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO directories (alias, path, created_at) VALUES (?, ?, ?)",
                  (alias, path, datetime.now()))
        conn.commit()
        print(f"✓ Created: {alias} → {path}")
    except sqlite3.IntegrityError:
        # Update existing
        c.execute("UPDATE directories SET path = ? WHERE alias = ?", (path, alias))
        conn.commit()
        print(f"✓ Updated: {alias} → {path}")
    finally:
        conn.close()


def add_command(alias, command):
    """Add a command shortcut"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO commands (alias, command, created_at) VALUES (?, ?, ?)",
                  (alias, command, datetime.now()))
        conn.commit()
        print(f"✓ Created command: {alias} → {command}")
    except sqlite3.IntegrityError:
        # Update existing
        c.execute("UPDATE commands SET command = ? WHERE alias = ?", (command, alias))
        conn.commit()
        print(f"✓ Updated command: {alias} → {command}")
    finally:
        conn.close()


def get_directory(alias):
    """Get directory path for an alias"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT path FROM directories WHERE alias = ?", (alias,))
    result = c.fetchone()

    # Update usage count
    if result:
        c.execute("UPDATE directories SET uses = uses + 1 WHERE alias = ?", (alias,))
        conn.commit()

    conn.close()
    return result[0] if result else None


def get_command(alias):
    """Get command for an alias"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT command FROM commands WHERE alias = ?", (alias,))
    result = c.fetchone()

    # Update usage count
    if result:
        c.execute("UPDATE commands SET uses = uses + 1 WHERE alias = ?", (alias,))
        conn.commit()

    conn.close()
    return result[0] if result else None


def list_all():
    """List all shortcuts"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get directories
    c.execute("SELECT alias, path, uses FROM directories ORDER BY uses DESC, alias")
    dirs = c.fetchall()

    # Get commands
    c.execute("SELECT alias, command, uses FROM commands ORDER BY uses DESC, alias")
    cmds = c.fetchall()

    conn.close()

    if dirs:
        print("\n📁 Directory shortcuts:")
        print("-" * 60)
        for alias, path, uses in dirs:
            # Shorten home directory
            display_path = path.replace(os.path.expanduser("~"), "~")
            print(f"{alias:<15} → {display_path:<40} ({uses} uses)")

    if cmds:
        print("\n⚡ Command shortcuts:")
        print("-" * 60)
        for alias, command, uses in cmds:
            # Truncate long commands
            display_cmd = command if len(command) <= 40 else command[:37] + "..."
            print(f"{alias:<15} → {display_cmd:<40} ({uses} uses)")

    if not dirs and not cmds:
        print("No shortcuts yet! Create one with:")
        print("  hop2 add <alias>           # Add current directory")
        print("  hop2 cmd <alias> <command> # Add command shortcut")


def remove_shortcut(alias):
    """Remove a shortcut"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Try directories first
    c.execute("DELETE FROM directories WHERE alias = ?", (alias,))
    if c.rowcount > 0:
        print(f"✓ Removed directory shortcut: {alias}")
    else:
        # Try commands
        c.execute("DELETE FROM commands WHERE alias = ?", (alias,))
        if c.rowcount > 0:
            print(f"✓ Removed command shortcut: {alias}")
        else:
            print(f"✗ No shortcut found: {alias}")

    conn.commit()
    conn.close()


def generate_cd_command(alias):
    """Generate cd command for shell integration"""
    path = get_directory(alias)
    if path:
        # This will be captured by shell function
        print(f"__HOP2_CD:{path}")
        return True
    return False


def run_command(alias, extra_args=None):
    """Run a command shortcut"""
    command = get_command(alias)
    if command:
        if extra_args:
            command = f"{command} {' '.join(extra_args)}"
        print(f"→ Running: {command}")
        subprocess.run(command, shell=True)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='hop2 - Quick directory and command shortcuts')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Add directory
    add_parser = subparsers.add_parser('add', help='Add directory shortcut (current dir by default)')
    add_parser.add_argument('alias', help='Shortcut name')
    add_parser.add_argument('path', nargs='?', help='Directory path (optional, defaults to current)')

    # Add command
    cmd_parser = subparsers.add_parser('cmd', help='Add command shortcut')
    cmd_parser.add_argument('alias', help='Shortcut name')
    cmd_parser.add_argument('command', nargs='+', help='Command to run')

    # List
    subparsers.add_parser('list', help='List all shortcuts')

    # Remove
    rm_parser = subparsers.add_parser('rm', help='Remove a shortcut')
    rm_parser.add_argument('alias', help='Shortcut to remove')

    # Go (for shell integration)
    go_parser = subparsers.add_parser('go', help='Go to directory (used by shell function)')
    go_parser.add_argument('alias', help='Directory shortcut')

    # Parse args
    args, unknown = parser.parse_known_args()

    # Initialize DB
    init_db()

    # Handle commands
    if args.command == 'add':
        add_directory(args.alias, args.path)
    elif args.command == 'cmd':
        command = ' '.join(args.command)
        add_command(args.alias, command)
    elif args.command == 'list':
        list_all()
    elif args.command == 'rm':
        remove_shortcut(args.alias)
    elif args.command == 'go':
        # Special command for shell integration
        if not generate_cd_command(args.alias):
            print(f"✗ No directory shortcut: {args.alias}")
            sys.exit(1)
    elif len(sys.argv) > 1:
        # Try to run as shortcut
        alias = sys.argv[1]

        # First check if it's a command
        if run_command(alias, sys.argv[2:]):
            return

        # Then check if it's a directory (for shell function)
        if generate_cd_command(alias):
            return

        print(f"✗ No shortcut found: {alias}")
        sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()