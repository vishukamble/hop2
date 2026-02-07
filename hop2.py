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
import urllib.request
import tempfile
import shutil
import json
import re
import shlex

# Config
DB_PATH = os.path.expanduser("~/.hop2/hop2.db")
DB_DIR = os.path.dirname(DB_PATH)

# Reserved words
RESERVED_ALIASES = {
    'add', 'cmd', 'list', 'ls', 'rm', 'go', 'update',
    'backup', 'restore', 'uninstall',
    'help', '--help', '-h',
    '--update', '--backup', '--restore', '--uninstall'
}
ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

def validate_alias(alias: str) -> bool:
    if alias in RESERVED_ALIASES:
        print(f"❌ '{alias}' is a reserved keyword and cannot be used.")
        return False
    if not ALIAS_PATTERN.fullmatch(alias):
        print("❌ Invalid alias. Use letters, numbers, ., _, - (max 64 chars, must start with alnum).")
        return False
    return True

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
    print(f"{'  --backup [file]':<25} Backup shortcuts to JSON")
    print(f"{'  --restore <file>':<25} Restore from JSON backup")
    print(f"{'  --update':<25} Update hop2 to latest")
    print(f"{'  --uninstall':<25} Remove hop2 completely")
    print("\nExamples:")
    print("  hop2 add work          # Save current dir as 'work'")
    print("  hop2 work              # Jump to work directory")
    print("  hop2 cmd gs 'git status'")
    print("  hop2 gs                # Run git status")
    print("  hop2 --backup          # Backup to timestamped file")
    print("  hop2 --restore backup.json  # Restore from backup")
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
    """Add or update a directory shortcut."""
    if not validate_alias(alias):
        return 1

    if path is None:
        path = os.getcwd()
    else:
        path = os.path.abspath(os.path.expanduser(path))

    if not os.path.isdir(path):
        print(f"❌ Directory does not exist: {path}")
        return 1

    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()

        # Prevent alias collision across tables
        c.execute("SELECT 1 FROM commands WHERE alias = ?", (alias,))
        if c.fetchone():
            print(f"❌ Alias '{alias}' already exists as a command shortcut.")
            return 1

        c.execute("""
            INSERT INTO directories (alias, path, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(alias) DO UPDATE SET path = excluded.path
        """, (alias, path, created))

        # Optional: detect create vs update
        print(f"✅ Saved: {alias} → {path}")
    return 0


def add_command(alias, cmd_parts):
    """Add or update a command shortcut."""
    if not validate_alias(alias):
        return 1

    command = ' '.join(cmd_parts).strip()
    if not command:
        print("❌ Command cannot be empty.")
        return 1

    created = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        c = conn.cursor()

        # Prevent alias collision across tables
        c.execute("SELECT 1 FROM directories WHERE alias = ?", (alias,))
        if c.fetchone():
            print(f"❌ Alias '{alias}' already exists as a directory shortcut.")
            return 1

        c.execute("""
            INSERT INTO commands (alias, command, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(alias) DO UPDATE SET command = excluded.command
        """, (alias, command, created))

        print(f"✅ Saved command: {alias} → {command}")
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
        print("\n📁 Directory Shortcuts (Hopper is ready to jump!)")
        print("─" * 70)

        dir_paths = [d['path'] for d in dirs]
        try:
            common_base = os.path.commonpath(dir_paths) if len(dir_paths) > 1 else os.path.dirname(dir_paths[0])
        except ValueError:
            common_base = os.path.expanduser("~")

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
    if not cmd:
        return None  # alias not found

    suffix = f" {shlex.join(extra_args)}" if extra_args else ""
    full = f"{cmd}{suffix}"
    print(f"→ Running: {full}")

    result = subprocess.run(full, shell=True)
    return result.returncode


def backup_data(filename=None):
    """Backup hop2 data to a JSON file"""
    if filename is None:
        # Default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hop2_backup_{timestamp}.json"

    backup_data = {
        "version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database": {
            "directories": [],
            "commands": []
        }
    }

    with get_conn() as conn:
        c = conn.cursor()

        # Get directories
        c.execute("SELECT alias, path, created_at, uses FROM directories")
        for row in c.fetchall():
            backup_data["database"]["directories"].append({
                "alias": row[0],
                "path": row[1],
                "created_at": row[2],
                "uses": row[3]
            })

        # Get commands
        c.execute("SELECT alias, command, created_at, uses FROM commands")
        for row in c.fetchall():
            backup_data["database"]["commands"].append({
                "alias": row[0],
                "command": row[1],
                "created_at": row[2],
                "uses": row[3]
            })

    # Write to file
    with open(filename, 'w') as f:
        json.dump(backup_data, f, indent=2)

    total_dirs = len(backup_data["database"]["directories"])
    total_cmds = len(backup_data["database"]["commands"])

    print(f"✅ Backup saved to: {filename}")
    print(f"   • {total_dirs} directories")
    print(f"   • {total_cmds} commands")
    return 0


def restore_data(filename):
    """Restore hop2 data from a JSON file"""
    if not os.path.exists(filename):
        print(f"❌ Backup file not found: {filename}")
        return 1

    try:
        with open(filename, 'r') as f:
            backup_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading backup file: {e}")
        return 1

    # Initialize database if it doesn't exist
    init_db()

    # Handle both v1.0 (flat) and v2.0 (database) backup formats
    version = backup_data.get("version", "1.0")

    if version == "2.0" and "database" in backup_data:
        # New format with database structure
        directories = backup_data["database"].get("directories", [])
        commands = backup_data["database"].get("commands", [])
    else:
        # Old format (v1.0) - flat structure
        directories = backup_data.get("directories", [])
        commands = backup_data.get("commands", [])

    # Ask for confirmation
    print(f"\n📦 Restore from: {filename}")
    print(f"   • Format version: {version}")
    print(f"   • {len(directories)} directories")
    print(f"   • {len(commands)} commands")
    print("\n⚠️  This will merge with existing shortcuts.")
    ans = input("Continue? [y/N]: ")
    if ans.lower() != 'y':
        print("❌ Restore cancelled.")
        return 1

    restored = {"dirs": 0, "cmds": 0}

    with get_conn() as conn:
        c = conn.cursor()

        # Restore directories
        for d in directories:
            try:
                c.execute("""
                    INSERT OR REPLACE INTO directories (alias, path, created_at, uses) 
                    VALUES (?, ?, ?, ?)
                """, (d['alias'], d['path'], d.get('created_at'), d.get('uses', 0)))
                restored["dirs"] += 1
            except Exception as e:
                print(f"⚠️  Skipped directory {d['alias']}: {e}")

        # Restore commands
        for cmd in commands:
            try:
                c.execute("""
                    INSERT OR REPLACE INTO commands (alias, command, created_at, uses) 
                    VALUES (?, ?, ?, ?)
                """, (cmd['alias'], cmd['command'], cmd.get('created_at'), cmd.get('uses', 0)))
                restored["cmds"] += 1
            except Exception as e:
                print(f"⚠️  Skipped command {cmd['alias']}: {e}")

    print(f"\n✅ Restore complete!")
    print(f"   • Restored {restored['dirs']} directories")
    print(f"   • Restored {restored['cmds']} commands")
    return 0


def update_me(_=None):
    print("Updating hop2...")
    tmp = None
    try:
        with urllib.request.urlopen('https://install.hop2.tech', timeout=15) as resp:
            data = resp.read()

        with tempfile.NamedTemporaryFile('wb', delete=False) as f:
            f.write(data)
            tmp = f.name

        result = subprocess.run(['bash', tmp], check=False)
        if result.returncode != 0:
            print(f"❌ Update installer exited with code {result.returncode}")
            return result.returncode

        print("✅ Update complete.")
        return 0
    except Exception as e:
        print(f"❌ Update failed: {e}")
        return 1
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)



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
                errors.append(f"Couldn't remove from {d}: {e}")

    # 2) Remove ~/.hop2 data directory
    hop2_dir = os.path.expanduser('~/.hop2')
    dir_removed = False
    if os.path.isdir(hop2_dir):
        try:
            shutil.rmtree(hop2_dir)
            dir_removed = True
        except OSError as e:
            errors.append(f"Couldn't remove {hop2_dir}: {e}")

    # 3) Clean up shell RC files
    shell_cleaned = []
    for rc in ['.bashrc', '.bash_profile', '.zshrc', '.zprofile']:
        path = os.path.expanduser(f"~/{rc}")
        if not os.path.exists(path):
            continue

        # Remove hop2 integration lines (both comment and source)
        try:
            with open(path, 'r') as f:
                lines = f.readlines()

            new_lines = []
            skip_next = False

            for i, line in enumerate(lines):
                # Check if this is the hop2 comment line
                if line.strip() == '# hop2 shell integration':
                    # Check if the next line is the source command
                    if i + 1 < len(lines) and lines[i + 1].strip() == 'source ~/.hop2/init.sh':
                        skip_next = True  # Skip both this line and the next
                        continue
                    # If it's just an orphaned comment, skip it
                    continue

                # Skip the source line if it follows the comment
                if skip_next and line.strip() == 'source ~/.hop2/init.sh':
                    skip_next = False
                    continue

                # Also skip any standalone source line (in case comment was manually removed)
                if line.strip() == 'source ~/.hop2/init.sh':
                    continue

                new_lines.append(line)

            # Write back the cleaned content
            with open(path, 'w') as f:
                f.writelines(new_lines)

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
    parser.add_argument('--backup', nargs='?', const=True, metavar='FILE',
                        help="Backup hop2 data to JSON file (default: hop2_backup_TIMESTAMP.json)")
    parser.add_argument('--restore', metavar='FILE', help="Restore hop2 data from JSON backup file")

    # Parse only the known flags, leave the rest for sub-command/alias handling
    args, remainder = parser.parse_known_args()

    # Handle top-level flags immediately
    if args.uninstall:
        sys.exit(uninstall_me())

    if args.update:
        sys.exit(update_me())

    if args.backup:
        sys.exit(backup_data() if args.backup is True else backup_data(args.backup))

    if args.restore:
        sys.exit(restore_data(args.restore))

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

    known_subcommands = {'add', 'cmd', 'list', 'rm', 'update'}
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

        cmd_rc = run_command(alias, extra_args)
        if cmd_rc is not None:
            sys.exit(cmd_rc)

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