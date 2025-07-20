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
    print("\nhop2 - Quick directory jumping and command aliasing\n")
    print("Usage: hop2 <command> [args]")
    print("       hop2 <alias>        # Jump to directory or run command\n")

    print("Commands:")
    print("─" * 50)
    print(f"{'  add <alias> [path]':<25} Add directory shortcut")
    print(f"{'  cmd <alias> <command>':<25} Add command shortcut")
    print(f"{'  list, ls':<25} List all shortcuts")
    print(f"{'  rm <alias>':<25} Remove a shortcut")
    print(f"{'  update-me':<25} Update hop2 to latest")
    print(f"{'  uninstall-me':<25} Uninstall hop2")
    print("\nExamples:")
    print("  hop2 add work          # Save current dir as 'work'")
    print("  hop2 work              # Jump to work directory")
    print("  hop2 cmd gs 'git status'")
    print("  hop2 gs                # Run git status")
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
                         TEXT,
                         uses
                         INTEGER
                         DEFAULT
                         0
                     )''')
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
                         TEXT,
                         uses
                         INTEGER
                         DEFAULT
                         0
                     )''')


def add_directory(alias, path=None):
    """Add a directory shortcut"""
    if alias in RESERVED_ALIASES:
        print(f"❌ '{alias}' is a reserved keyword and cannot be used.")
        return 1

    if path is None:
        path = os.getcwd()
    else:
        path = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(path):
        print(f"❌ Path does not exist: {path}")
        return 1

    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO directories (alias, path, created_at) VALUES (?, ?, ?)",
                (alias, path, created)
            )
            print(f"✅ Created: {alias} → {path}")
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE directories SET path = ? WHERE alias = ?", (path, alias)
            )
            print(f"✅ Updated: {alias} → {path}")
    return 0


def add_command(alias, cmd_parts):
    """Add a command shortcut"""
    if alias in RESERVED_ALIASES:
        print(f"❌ '{alias}' is a reserved keyword and cannot be used.")
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
            print(f"✅ Created command: {alias} → {command}")
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE commands SET command = ? WHERE alias = ?", (command, alias)
            )
            print(f"✅ Updated command: {alias} → {command}")
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
    """Lists all shortcuts, visualizing directory paths from a common root."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row  # Make sure we can access columns by name
        c = conn.cursor()
        c.execute("SELECT alias, path, uses FROM directories ORDER BY path")
        dirs = c.fetchall()
        c.execute("SELECT alias, command, uses FROM commands ORDER BY uses DESC, alias")
        cmds = c.fetchall()

    if dirs:
        print("\n📁 Directory Shortcuts (Mario is ready to jump!)")
        print("─" * 70)

        dir_paths = [d['path'] for d in dirs]
        # Find the longest common starting path
        common_base = os.path.commonpath(dir_paths) if len(dir_paths) > 1 else os.path.dirname(dir_paths[0])

        # Don't show the user's home dir in the common path, replace with ~
        home_dir = os.path.expanduser("~")
        display_base = f"~{common_base[len(home_dir):]}" if common_base.startswith(home_dir) else common_base
        print(f"🌲 Common Root: {display_base}/\n")

        for d in dirs:
            # Show the part of the path that is *not* common
            relative_path = os.path.relpath(d['path'], common_base)
            print(f"  {d['alias']:<15} → ./{relative_path:<40} ({d['uses']} uses)")

        # The 'r' before the """ fixes the SyntaxWarning
        print(r"""
                     .--.
                    |o_o |
                    |:_/ |
                   //   \ \
                  (|     | )
                 /'\_   _/`\
                 \___)=(___/
        """)

    if cmds:
        print("\n⚡ Command Shortcuts")
        print("─" * 70)
        for alias, command, uses in cmds:
            display_cmd = command if len(command) <= 45 else f"{command[:42]}..."
            print(f"  {alias:<15} → {display_cmd:<45} ({uses} uses)")

    if not dirs and not cmds:
        print("No shortcuts yet. Go add some! `hop2 add <alias>`")


def remove_shortcut(alias):
    """Remove a directory or command shortcut."""
    with get_conn() as conn:
        c = conn.cursor()
        # Try to delete from directories
        c.execute("DELETE FROM directories WHERE alias = ?", (alias,))
        if c.rowcount:
            print(f"✅ Removed directory shortcut: {alias}")
            return 0
        # If not found, try to delete from commands
        c.execute("DELETE FROM commands WHERE alias = ?", (alias,))
        if c.rowcount:
            print(f"✅ Removed command shortcut: {alias}")
            return 0
    # If not found in either table
    print(f"❌ No shortcut found with the alias: {alias}")
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
        print(f"❌ Update failed: {e}")
        return 1


def uninstall_me(_=None):
    """A comprehensive uninstaller that removes files and cleans up shell configs."""
    print("\n🗑️  Are you sure you want to uninstall hop2?\n")
    ans = input("This will remove the executable, data, and the source line from your shell config.\n"
                "Type 'yes' to confirm: ")
    if ans.lower() != 'yes':
        print("❌ Uninstallation cancelled.")
        return 1

    print("\n📦 Uninstalling hop2...\n")

    removed_from = []
    errors = []

    # 1) Remove hop2 executable from common install locations
    for d in ['/usr/local/bin', os.path.expanduser('~/.local/bin'), os.path.expanduser('~/bin')]:
        p = os.path.join(d, 'hop2')
        if os.path.exists(p):
            try:
                os.remove(p)
                removed_from.append(d)
            except OSError as e:
                errors.append(f"Couldn’t remove from {d}: {e}")

    # 2) Remove ~/.hop2 data directory
    hop2_dir = os.path.expanduser('~/.hop2')
    dir_removed = False
    if os.path.isdir(hop2_dir):
        try:
            shutil.rmtree(hop2_dir)
            dir_removed = True
        except OSError as e:
            errors.append(f"Couldn’t remove {hop2_dir}: {e}")

    # 3) Clean up shell RC files
    shell_cleaned = []
    for rc in ['.bashrc', '.zshrc']:
        path = os.path.expanduser(f"~/{rc}")
        if not os.path.exists(path):
            continue

        # remove any line that exactly matches 'source ~/.hop2/init.sh'
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
            with open(path, 'w') as f:
                for line in lines:
                    if line.strip() == 'source ~/.hop2/init.sh':
                        continue
                    f.write(line)
            shell_cleaned.append(rc)
        except Exception as e:
            errors.append(f"Failed to clean {rc}: {e}")

    # 4) Final report
    print("┌──────────────────────────────────────────╥────────┐")
    print("│ Action                                   ║ Status │")
    print("╞══════════════════════════════════════════╫════════╡")
    print(f"│ Removed hop2 executable                  ║ {'✅' if removed_from else 'n/a'}    │")
    print(f"│ Removed ~/.hop2 data directory           ║ {'✅' if dir_removed else 'n/a'}    │")
    print(f"│ Cleaned shell config (.bashrc/.zshrc)    ║ {'✅' if shell_cleaned else 'n/a'}    │")
    print("└──────────────────────────────────────────╨────────┘\n")

    if errors:
        print("⚠️  Some issues encountered:")
        for e in errors:
            print(f"  • {e}")
        print()

    print("✅ hop2 has been uninstalled.")
    if not shell_cleaned:
        print("⚠️  Manual cleanup required: remove")
        print("    source ~/.hop2/init.sh")
        print("  from your shell RC file.\n")

    print("Please restart your shell to complete uninstallation.")
    return 0



def main():
    # Use argparse from the start to handle flags like --uninstall and --help
    parser = argparse.ArgumentParser(
        description="hop2 - Quick directory jumping and command aliasing",
        add_help=False  # We use a custom help function
    )
    parser.add_argument('-h', '--help', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--uninstall', action='store_true', help="Uninstall hop2 from your system.")
    parser.add_argument('--update', action='store_true', help="Update hop2 to the latest version.")

    # Parse only the known flags, leave the rest for sub-command/alias handling
    args, remainder = parser.parse_known_args()

    # Handle top-level flags immediately
    if args.help:
        print_help()
        sys.exit(0)

    if args.uninstall:
        uninstall_me()
        sys.exit(0)

    if args.update:
        update_me()
        sys.exit(0)

    # If no remaining args, show help
    if not remainder:
        print_help()
        sys.exit(0)

    # The actual command is the first remaining argument
    sys.argv = [sys.argv[0]] + remainder
    command_to_run = sys.argv[1]

    # Alias 'ls' to 'list'
    if command_to_run == 'ls':
        sys.argv[1] = 'list'
        command_to_run = 'list'

    known_subcommands = {'add', 'cmd', 'list', 'rm'}
    init_db()

    # If it's NOT a known subcommand, treat it as a custom alias
    # In your main() function, update the alias-handling block:
    # If it's NOT a known subcommand, treat it as a custom alias
    if command_to_run not in known_subcommands:
        alias = command_to_run
        extra_args = sys.argv[2:]

        path = get_directory(alias)
        if path:
            if extra_args:
                # New emoji for this error
                print(f"❌ Directory shortcuts do not accept arguments. Did you mean 'cd {path}'?")
                sys.exit(1)
            print(f"__HOP2_CD:{path}")
            sys.exit(0)

        if run_command(alias, extra_args):
            sys.exit(0)

        # New emoji for the final "not found" error
        print(f"❌ No shortcut '{alias}' found. Try 'hop2 list'.")
        sys.exit(1)

    # If we are here, it IS a known subcommand, so use a new parser
    sub_parser = argparse.ArgumentParser(add_help=False)
    sp = sub_parser.add_subparsers(dest='command', required=True)

    # Add other parsers...
    p_add = sp.add_parser('add')
    p_add.add_argument('alias')
    p_add.add_argument('path', nargs='?')
    p_add.set_defaults(func=lambda a: add_directory(a.alias, a.path))

    p_cmd = sp.add_parser('cmd')
    p_cmd.add_argument('alias')
    p_cmd.add_argument('cmd_str', nargs='+')
    p_cmd.set_defaults(func=lambda a: add_command(a.alias, a.cmd_str))

    p_list = sp.add_parser('list')
    p_list.set_defaults(func=lambda a: list_all())

    p_rm = sp.add_parser('rm')
    p_rm.add_argument('alias')
    p_rm.set_defaults(func=lambda a: remove_shortcut(a.alias))

    p = sp.add_parser('update', help='Alias for update')
    p.set_defaults(func=lambda a: update_me())

    try:
        parsed_args = sub_parser.parse_args()
        if hasattr(parsed_args, 'func'):
            code = parsed_args.func(parsed_args)
            sys.exit(code if isinstance(code, int) else 0)
    except SystemExit as e:
        sys.exit(e.code)


if __name__ == "__main__":
    main()
