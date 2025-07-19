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

# ‹change›: Reserved words you cannot override
RESERVED_ALIASES = [
    'add', 'cmd', 'list', 'rm', 'go',
    'update-me', 'uninstall-me',
    'help', '--help', '-h'
]


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
    if alias in RESERVED_ALIASES:                                  # ‹change›
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
    if alias in RESERVED_ALIASES:                                  # ‹change›
        print(f"✗ '{alias}' is reserved and cannot be used")
        return 1

    command = ' '.join(cmd_parts)                                  # ‹change›
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
    """Get the directory path for an alias"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT path FROM directories WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE directories SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row[0]
    return None


def get_command(alias):
    """Get command for an alias"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT command FROM commands WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE commands SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row[0]
    return None


def list_all(_=None):
    """List all shortcuts"""
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
    """Remove a shortcut"""
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
    """Generate cd command for shell integration"""
    path = get_directory(alias)
    if path:
        print(f"__HOP2_CD:{path}")
        return True
    return False


def run_command(alias, extra_args=None):
    """Run a command shortcut"""
    cmd = get_command(alias)
    if cmd:
        full = f"{cmd} {' '.join(extra_args)}" if extra_args else cmd
        print(f"→ Running: {full}")
        subprocess.run(full, shell=True)
        return True
    return False


def update_me(_=None):                                              # ‹change›
    """Self-update hop2"""
    print("Updating hop2…")
    data = urllib.request.urlopen(
        'https://raw.githubusercontent.com/vishukamble/hop2/main/install.sh'
    ).read()
    with tempfile.NamedTemporaryFile('wb', delete=False) as f:
        f.write(data)
        tmp = f.name
    subprocess.run(['bash', tmp])
    os.unlink(tmp)
    return 0


def uninstall_me(_=None):                                           # ‹change›
    """Self-uninstall hop2"""
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
    parser = argparse.ArgumentParser(description='hop2 - Quick directory and command shortcuts')
    sp = parser.add_subparsers(dest='command')

    # add
    p_add = sp.add_parser('add', help='Add directory shortcut')
    p_add.add_argument('alias')
    p_add.add_argument('path', nargs='?')
    p_add.set_defaults(func=lambda args: add_directory(args.alias, args.path))

    # cmd ‹change›
    p_cmd = sp.add_parser('cmd', help='Add command shortcut')
    p_cmd.add_argument('alias')
    p_cmd.add_argument('cmd', nargs='+', help='Command to run')
    p_cmd.set_defaults(func=lambda args: add_command(args.alias, args.cmd))

    # list
    p_list = sp.add_parser('list', help='List all shortcuts')
    p_list.set_defaults(func=list_all)

    # rm
    p_rm = sp.add_parser('rm', help='Remove a shortcut')
    p_rm.add_argument('alias')
    p_rm.set_defaults(func=lambda args: remove_shortcut(args.alias))

    # go (internal)
    p_go = sp.add_parser('go', help=argparse.SUPPRESS)
    p_go.add_argument('alias')
    p_go.set_defaults(func=lambda args: (generate_cd_command(args.alias) or sys.exit(1)))

    # update-me ‹change›
    p_up = sp.add_parser('update-me', help='Self-update hop2')
    p_up.set_defaults(func=update_me)

    # uninstall-me ‹change›
    p_un = sp.add_parser('uninstall-me', help='Self-uninstall hop2')
    p_un.set_defaults(func=uninstall_me)

    # default
    parser.set_defaults(func=lambda args: parser.print_help())

    args = parser.parse_args()
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
