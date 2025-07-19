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
import urllib.request
import tempfile
import shutil

# Config
DB_PATH = os.path.expanduser("~/.hop2/hop2.db")
DB_DIR = os.path.dirname(DB_PATH)

# Reserved words
RESERVED_ALIASES = [
    'add', 'cmd', 'list', 'rm', 'go',
    'update-me', 'uninstall-me',
    'help', '--help', '-h'
]

def print_help():
    """Custom table-formatted help"""
    print("Usage: hop2 <command> [args]\n")
    print(f"{'Command':<15} What it does")
    print("-" * 50)
    for cmd, desc in [
        ("update-me",    "Update hop2 to the latest version"),
        ("uninstall-me", "Uninstall hop2"),
        ("add",          "Add directory shortcut (current dir by default)"),
        ("cmd",          "Add command shortcut"),
        ("list",         "List all shortcuts"),
        ("rm",           "Remove a shortcut"),
        ("go",           "(internal)")
    ]:
        print(f"{cmd:<15} {desc}")
    print()
    sys.exit(0)


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
    """Add a directory shortcut"""
    if alias in RESERVED_ALIASES:
        print(f"✗ '{alias}' is reserved and cannot be used")
        return 1

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
            c.execute(
                "UPDATE directories SET path = ? WHERE alias = ?", (path, alias)
            )
            print(f"✓ Updated: {alias} → {path}")
    return 0


def add_command(alias, cmd_parts):
    """Add a command shortcut"""
    if alias in RESERVED_ALIASES:
        print(f"✗ '{alias}' is reserved and cannot be used")
        return 1

    command = ' '.join(cmd_parts)
    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO commands (alias, command, created_at) VALUES (?, ?, ?)",
                (alias, command, created)
            )
            print(f"✓ Created command: {alias} → {command}")
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE commands SET command = ? WHERE alias = ?", (command, alias)
            )
            print(f"✓ Updated command: {alias} → {command}")
    return 0


def get_directory(alias):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT path FROM directories WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE directories SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row[0]
    return None


def get_command(alias):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT command FROM commands WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE commands SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row[0]
    return None


def list_all(_=None):
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
            display_cmd = command if len(command) <= 40 else command[:37] + "..."
            print(f"{alias:<15} → {display_cmd:<40} ({uses} uses)")

    if not dirs and not cmds:
        print("No shortcuts yet; run `hop2 add <alias>` or `hop2 cmd <alias> <command>`")


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


def run_command(alias, extra_args=None):
    cmd = get_command(alias)
    if cmd:
        full = f"{cmd} {' '.join(extra_args)}" if extra_args else cmd
        print(f"→ Running: {full}")
        subprocess.run(full, shell=True)
        return True
    return False


def update_me(_=None):
    print("Updating hop2...")
    try:
        data = urllib.request.urlopen(
            'https://raw.githubusercontent.com/vishukamble/hop2/main/install.sh'
        ).read()
        with tempfile.NamedTemporaryFile('wb', delete=False) as f:
            f.write(data)
            tmp = f.name
        subprocess.run(['bash', tmp])
        os.unlink(tmp)
        return 0
    except Exception as e:
        print(f"✗ Update failed: {e}")
        return 1


def uninstall_me(_=None):
    ans = input("Are you sure you want to uninstall hop2? (y/N): ").lower()
    if ans != 'y':
        print("Cancelled.")
        return 1

    print("Uninstalling hop2…")
    for d in ['/usr/local/bin', os.path.expanduser('~/.local/bin'), os.path.expanduser('~/bin')]:
        p = os.path.join(d, 'hop2')
        if os.path.exists(p):
            os.remove(p)
            print(f"✓ Removed {p}")
    shutil.rmtree(os.path.expanduser('~/.hop2'), ignore_errors=True)
    print("\nTo complete uninstall, remove `source ~/.hop2/init.sh` from your RC.")
    return 0


def main():
    # if no args or help flag, show our custom help
    if len(sys.argv) == 1 or sys.argv[1] in ('-h', '--help'):
        print_help()

    parser = argparse.ArgumentParser(add_help=False)
    sp = parser.add_subparsers(dest='command')

    p = sp.add_parser('add', help=argparse.SUPPRESS)
    p.add_argument('alias')
    p.add_argument('path', nargs='?')
    p.set_defaults(func=lambda a: add_directory(a.alias, a.path))

    p = sp.add_parser('cmd', help=argparse.SUPPRESS)
    p.add_argument('alias')
    p.add_argument('cmd', nargs='+')
    p.set_defaults(func=lambda a: add_command(a.alias, a.cmd))

    p = sp.add_parser('list', help=argparse.SUPPRESS)
    p.set_defaults(func=list_all)

    p = sp.add_parser('rm', help=argparse.SUPPRESS)
    p.add_argument('alias')
    p.set_defaults(func=lambda a: remove_shortcut(a.alias))

    p = sp.add_parser('go', help=argparse.SUPPRESS)
    p.add_argument('alias')
    p.set_defaults(func=lambda a: (generate_cd_command(a.alias) or sys.exit(1)))

    p = sp.add_parser('update-me', help=argparse.SUPPRESS)
    p.set_defaults(func=update_me)

    p = sp.add_parser('uninstall-me', help=argparse.SUPPRESS)
    p.set_defaults(func=uninstall_me)

    args = parser.parse_args()
    init_db()

    # fallback: run or cd shortcut
    if args.command is None:
        alias = sys.argv[1]
        if run_command(alias, sys.argv[2:]):
            sys.exit(0)
        if generate_cd_command(alias):
            sys.exit(0)
        print(f"✗ No shortcut found: {alias}")
        sys.exit(1)

    code = args.func(args)
    sys.exit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()
