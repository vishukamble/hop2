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
    """Initialize the database tables if they don’t exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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
    """Add or update a directory shortcut."""
    if path is None:
        path = os.getcwd()
    else:
        path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(path):
        print(f"✗ Path does not exist: {path}", file=sys.stderr)
        return 1

    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO directories(alias, path, created_at) VALUES (?, ?, ?)",
                (alias, path, created)
            )
            print(f"✓ Created: {alias} → {path}")
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE directories SET path = ? WHERE alias = ?",
                (path, alias)
            )
            print(f"✓ Updated: {alias} → {path}")
    return 0

def add_command(alias, cmd):
    """Add or update a command shortcut."""
    command_str = " ".join(cmd)
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO commands(alias, command, created_at) VALUES (?, ?, ?)",
                (alias, command_str, created)
            )
            print(f"✓ Created command: {alias} → {command_str}")
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE commands SET command = ? WHERE alias = ?",
                (command_str, alias)
            )
            print(f"✓ Updated command: {alias} → {command_str}")
    return 0

def list_all(_args=None):
    """List all directory + command shortcuts."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT alias, path, uses FROM directories ORDER BY uses DESC, alias")
        dirs = c.fetchall()
        c.execute("SELECT alias, command, uses FROM commands ORDER BY uses DESC, alias")
        cmds = c.fetchall()

    if dirs:
        print("\n📁 Directory shortcuts:")
        print("-" * 60)
        for alias, path, uses in dirs:
            disp = path.replace(os.path.expanduser("~"), "~")
            print(f"{alias:<15} → {disp:<40} ({uses} uses)")
    if cmds:
        print("\n⚡ Command shortcuts:")
        print("-" * 60)
        for alias, command, uses in cmds:
            disp = command if len(command) <= 40 else command[:37] + "..."
            print(f"{alias:<15} → {disp:<40} ({uses} uses)")
    if not dirs and not cmds:
        print("No shortcuts yet!")
        print("  hop2 add <alias>           # Add current directory")
        print("  hop2 cmd <alias> <command> # Add command shortcut")
    return 0

def remove_shortcut(alias):
    """Remove a directory or command shortcut."""
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

    print(f"✗ No shortcut found: {alias}", file=sys.stderr)
    return 1

def generate_cd_command(alias):
    """Emit a magic marker for the shell wrapper to cd."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT path FROM directories WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            print(f"__HOP2_CD:{row[0]}")
            with sqlite3.connect(DB_PATH) as conn2:
                conn2.execute("UPDATE directories SET uses = uses + 1 WHERE alias = ?", (alias,))
            return True
    return False

def run_command(alias, extra):
    """Run a stored command alias."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT command FROM commands WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            full = row[0] + (" " + " ".join(extra) if extra else "")
            print(f"→ Running: {full}")
            subprocess.run(full, shell=True)
            conn.execute("UPDATE commands SET uses = uses + 1 WHERE alias = ?", (alias,))
            return True
    return False

def main():
    parser = argparse.ArgumentParser(
        description="hop2 - Quick directory and command shortcuts"
    )
    subs = parser.add_subparsers(dest="command")

    # add
    p = subs.add_parser("add", help="Add directory shortcut")
    p.add_argument("alias")
    p.add_argument("path", nargs="?", default=None)
    p.set_defaults(func=lambda a: add_directory(a.alias, a.path))

    # cmd
    p = subs.add_parser("cmd", help="Add command shortcut")
    p.add_argument("alias")
    p.add_argument("cmd", nargs="+", help="The command to alias")
    p.set_defaults(func=lambda a: add_command(a.alias, a.cmd))

    # list
    p = subs.add_parser("list", help="List all shortcuts")
    p.set_defaults(func=list_all)

    # rm
    p = subs.add_parser("rm", help="Remove a shortcut")
    p.add_argument("alias")
    p.set_defaults(func=lambda a: remove_shortcut(a.alias))

    # internal go
    p = subs.add_parser("go", help=argparse.SUPPRESS)
    p.add_argument("alias")
    p.set_defaults(func=lambda a: (generate_cd_command(a.alias) or (_ for _ in ()).throw(SystemExit(1))))

    # default if nothing matched
    parser.set_defaults(func=lambda a: parser.print_help())

    args = parser.parse_args()
    init_db()

    # if user typed e.g. `hop2 gs ...`
    if args.command is None and len(sys.argv) > 1:
        alias = sys.argv[1]
        rest  = sys.argv[2:]
        if run_command(alias, rest):
            sys.exit(0)
        if generate_cd_command(alias):
            sys.exit(0)
        print(f"✗ No shortcut found: {alias}", file=sys.stderr)
        sys.exit(1)

    # dispatch
    code = args.func(args)
    sys.exit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()
