#!/usr/bin/env python3
"""
hop2 - Quick directory and command aliasing for the terminal
"""
import os
import sys
import sqlite3
import subprocess
import argparse
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

# Config
DB_PATH = os.path.expanduser("~/.hop2/hop2.db")
DB_DIR  = os.path.dirname(DB_PATH)

@contextmanager
def get_conn():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    """Initialize the database"""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS directories
                     (alias TEXT PRIMARY KEY,
                      path TEXT NOT NULL,
                      created_at TEXT,
                      uses INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS commands
                     (alias TEXT PRIMARY KEY,
                      command TEXT NOT NULL,
                      created_at TEXT,
                      uses INTEGER DEFAULT 0)''')

def add_directory(alias, path=None):
    """Add a directory shortcut"""
    if path is None:
        path = os.getcwd()
    else:
        path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        print(f"✗ Path does not exist: {path}")
        return 1

    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO directories (alias, path, created_at) VALUES (?, ?, ?)",
                (alias, path, created)
            )
            print(f"✓ Created: {alias} → {path}")
        except sqlite3.IntegrityError:
            c.execute("UPDATE directories SET path = ? WHERE alias = ?", (path, alias))
            print(f"✓ Updated: {alias} → {path}")
    return 0

def add_command(alias, command):
    """Add a command shortcut"""
    created = datetime.now(timezone.utc).isoformat()  # ← change: store ISO UTC
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO commands (alias, command, created_at) VALUES (?, ?, ?)",
                (alias, command, created)
            )
            print(f"✓ Created command: {alias} → {command}")
        except sqlite3.IntegrityError:
            c.execute("UPDATE commands SET command = ? WHERE alias = ?", (command, alias))
            print(f"✓ Updated command: {alias} → {command}")
    return 0

def get_directory(alias):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT path FROM directories WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE directories SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row["path"]
    return None

def get_command(alias):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT command FROM commands WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE commands SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row["command"]
    return None

def list_all():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT alias, path, uses FROM directories ORDER BY uses DESC, alias")
        dirs = c.fetchall()
        c.execute("SELECT alias, command, uses FROM commands ORDER BY uses DESC, alias")
        cmds = c.fetchall()

    if dirs:
        print("\n📁 Directory shortcuts:")
        print("-" * 60)
        for alias, path, uses in dirs:
            display = path.replace(os.path.expanduser("~"), "~")
            print(f"{alias:<15} → {display:<40} ({uses} uses)")
    if cmds:
        print("\n⚡ Command shortcuts:")
        print("-" * 60)
        for alias, command, uses in cmds:
            disp = command if len(command) <= 40 else command[:37] + "..."
            print(f"{alias:<15} → {disp:<40} ({uses} uses)")
    if not dirs and not cmds:
        print("No shortcuts yet! Create one with:")
        print("  hop2 add <alias>           # Add current directory")
        print("  hop2 cmd <alias> <command> # Add command shortcut")
    return 0

def remove_shortcut(alias):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM directories WHERE alias = ?", (alias,))
        if c.rowcount:
            print(f"✓ Removed directory shortcut: {alias}")
            return 0
        c.execute("DELETE FROM commands WHERE alias = ?", (alias,))
        if c.rowcount:
            print(f"✓ Removed command shortcut: {alias}")
            return 0
    print(f"✗ No shortcut found: {alias}")
    return 1

def generate_cd_command(alias):
    path = get_directory(alias)
    if path:
        print(f"__HOP2_CD:{path}")
        return True
    return False

def run_command(alias, extra):
    cmd = get_command(alias)
    if cmd:
        if extra:
            cmd = f"{cmd} {' '.join(extra)}"
        print(f"→ Running: {cmd}")
        subprocess.run(cmd, shell=True)
        return True
    return False

def main():
    parser = argparse.ArgumentParser(prog="hop2",
        description="hop2 - Quick directory and command shortcuts")
    sub = parser.add_subparsers(dest="command")

    # add
    p = sub.add_parser("add", help="Add directory shortcut")
    p.add_argument("alias")
    p.add_argument("path", nargs="?")
    p.set_defaults(func=lambda args: add_directory(args.alias, args.path))

    # cmd ← change: use 'command' not 'cmd', wire up func
    p = sub.add_parser("cmd", help="Add command shortcut")
    p.add_argument("alias", help="Shortcut name")
    p.add_argument("command", nargs="+", help="Command to run")
    p.set_defaults(func=lambda args: add_command(args.alias, " ".join(args.command)))

    # list
    p = sub.add_parser("list", help="List all shortcuts")
    p.set_defaults(func=lambda args: list_all())

    # rm
    p = sub.add_parser("rm", help="Remove a shortcut")
    p.add_argument("alias")
    p.set_defaults(func=lambda args: remove_shortcut(args.alias))

    # go (internal)
    p = sub.add_parser("go", help=argparse.SUPPRESS)
    p.add_argument("alias")
    p.set_defaults(func=lambda args: (generate_cd_command(args.alias) or
        (print(f"✗ No directory shortcut: {args.alias}"), sys.exit(1))))

    # default
    parser.set_defaults(func=lambda args: parser.print_help())

    args, extras = parser.parse_known_args()
    init_db()

    # bare alias fallback
    if args.command is None and len(sys.argv) > 1:
        alias = sys.argv[1]
        if run_command(alias, sys.argv[2:]):
            sys.exit(0)
        if generate_cd_command(alias):
            sys.exit(0)
        print(f"✗ No shortcut found: {alias}")
        sys.exit(1)

    # dispatch
    code = args.func(args)
    sys.exit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()
