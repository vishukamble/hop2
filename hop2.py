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
import json

# Config
DB_PATH = os.path.expanduser("~/.hop2/hop2.db")
DB_DIR = os.path.dirname(DB_PATH)

# Reserved words
RESERVED_ALIASES = [
    'add', 'cmd', 'list', 'rm', 'go',
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
        print("\n📁 Directory Shortcuts (Hopper is ready to jump!)")
        print("─" * 70)

        dir_paths = [d['path'] for d in dirs]
        # Find the longest common starting path
        # os.path.commonpath raises ValueError on Windows when paths span drives
        try:
            common_base = os.path.commonpath(dir_paths) if len(dir_paths) > 1 else os.path.dirname(dir_paths[0])
        except ValueError:
            common_base = None

        home_dir = os.path.expanduser("~")

        if common_base:
            # Use normcase for case-insensitive comparison on Windows
            if os.path.normcase(common_base).startswith(os.path.normcase(home_dir)):
                display_base = f"~{common_base[len(home_dir):]}"
            else:
                display_base = common_base
            print(f"🌲 Common Root: {display_base}/\n")

            for d in dirs:
                relative_path = os.path.relpath(d['path'], common_base)
                print(f"  {d['alias']:<15} → ./{relative_path:<40} ({d['uses']} uses)")
        else:
            # Paths span multiple drives — show full paths
            print()
            for d in dirs:
                print(f"  {d['alias']:<15} → {d['path']:<45} ({d['uses']} uses)")

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
        if sys.platform == 'win32':
            url = 'https://raw.githubusercontent.com/vishukamble/hop2/main/install.ps1'
            data = urllib.request.urlopen(url).read()
            with tempfile.NamedTemporaryFile('wb', suffix='.ps1', delete=False) as f:
                f.write(data)
                tmp = f.name
            subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', tmp])
        else:
            data = urllib.request.urlopen('https://install.hop2.tech').read()
            with tempfile.NamedTemporaryFile('wb', delete=False) as f:
                f.write(data)
                tmp = f.name
            subprocess.run(['bash', tmp])
        return 0
    except Exception as e:
        print(f"❌ Update failed: {e}")
        return 1
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def _get_windows_documents():
    """Get the actual Documents folder path, handling OneDrive redirection."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
        ) as key:
            docs_raw, _ = winreg.QueryValueEx(key, 'Personal')
            return os.path.expandvars(docs_raw)
    except Exception:
        return str(Path.home() / 'Documents')


def _get_windows_ps_profiles():
    """Return candidate PowerShell profile paths for PS 5.1 and PS 7+."""
    docs = _get_windows_documents()
    return [
        os.path.join(docs, 'WindowsPowerShell', 'Microsoft.PowerShell_profile.ps1'),  # PS 5.1
        os.path.join(docs, 'PowerShell', 'Microsoft.PowerShell_profile.ps1'),         # PS 7+
    ]


def _windows_remove_from_user_path(target_dir, errors):
    """Remove *target_dir* from the HKCU user PATH. Returns True if changed."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r'Environment', 0,
            winreg.KEY_READ | winreg.KEY_WRITE
        ) as key:
            try:
                current, _ = winreg.QueryValueEx(key, 'PATH')
            except FileNotFoundError:
                current = ''
            parts = [p for p in current.split(';') if p.strip()]
            norm_target = os.path.normcase(target_dir.rstrip('\\'))
            new_parts = [p for p in parts if os.path.normcase(p.rstrip('\\')) != norm_target]
            if len(new_parts) < len(parts):
                winreg.SetValueEx(key, 'PATH', 0, winreg.REG_EXPAND_SZ, ';'.join(new_parts))
                return True
    except Exception as e:
        errors.append(f"Couldn't update user PATH: {e}")
    return False


def _clean_ps_profile(path, errors):
    """Remove hop2 integration lines from a PowerShell profile. Returns True if changed."""
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        skip_next = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Comment sentinel
            if stripped == '# hop2 shell integration':
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
                if '.hop2' in next_line.lower() and 'init.ps1' in next_line.lower():
                    skip_next = True
                continue
            # Source line following the comment
            if skip_next and '.hop2' in stripped.lower() and 'init.ps1' in stripped.lower():
                skip_next = False
                continue
            # Standalone source line (comment was manually removed)
            if '.hop2' in stripped.lower() and 'init.ps1' in stripped.lower():
                continue
            new_lines.append(line)

        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        errors.append(f"Failed to clean {path}: {e}")
    return False


def _clean_unix_rc(rc_filename, errors):
    """Remove hop2 integration lines from a bash/zsh RC file. Returns True if changed."""
    path = os.path.expanduser(f"~/{rc_filename}")
    if not os.path.exists(path):
        return False
    try:
        with open(path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        skip_next = False
        for i, line in enumerate(lines):
            if line.strip() == '# hop2 shell integration':
                if i + 1 < len(lines) and lines[i + 1].strip() == 'source ~/.hop2/init.sh':
                    skip_next = True
                continue
            if skip_next and line.strip() == 'source ~/.hop2/init.sh':
                skip_next = False
                continue
            if line.strip() == 'source ~/.hop2/init.sh':
                continue
            new_lines.append(line)

        with open(path, 'w') as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        errors.append(f"Failed to clean {rc_filename}: {e}")
    return False


def uninstall_me(_=None):
    """A comprehensive uninstaller that removes files and cleans up shell configs."""
    print("\n🗑️  Are you sure you want to uninstall hop2?\n")
    ans = input("This will remove the executable, data, and the source line from your shell config.\n"
                "Type 'yes' to confirm: ")
    if ans.lower() != 'yes':
        print("❌ Uninstallation cancelled.")
        return 1

    print("\n📦 Uninstalling hop2...\n")

    errors = []
    removed_from = []
    path_cleaned = False
    dir_removed = False
    shell_cleaned = []

    # ------------------------------------------------------------------ #
    # 1) Remove executable / PATH entry (platform-specific)              #
    # ------------------------------------------------------------------ #
    if sys.platform == 'win32':
        bin_dir = str(Path.home() / '.hop2' / 'bin')
        path_cleaned = _windows_remove_from_user_path(bin_dir, errors)
        if path_cleaned:
            removed_from.append(bin_dir)
    else:
        for d in ['/usr/local/bin', os.path.expanduser('~/.local/bin'), os.path.expanduser('~/bin')]:
            p = os.path.join(d, 'hop2')
            if os.path.exists(p):
                try:
                    os.remove(p)
                    removed_from.append(d)
                except OSError as e:
                    errors.append(f"Couldn't remove from {d}: {e}")

    # ------------------------------------------------------------------ #
    # 2) Remove ~/.hop2 data directory (cross-platform)                  #
    # ------------------------------------------------------------------ #
    hop2_dir = os.path.expanduser('~/.hop2')
    if os.path.isdir(hop2_dir):
        try:
            shutil.rmtree(hop2_dir)
            dir_removed = True
        except OSError as e:
            errors.append(f"Couldn't remove {hop2_dir}: {e}")

    # ------------------------------------------------------------------ #
    # 3) Clean shell configs (platform-specific)                         #
    # ------------------------------------------------------------------ #
    if sys.platform == 'win32':
        for ps_profile in _get_windows_ps_profiles():
            if _clean_ps_profile(ps_profile, errors):
                shell_cleaned.append(os.path.basename(os.path.dirname(ps_profile)))
    else:
        for rc in ['.bashrc', '.zshrc']:
            if _clean_unix_rc(rc, errors):
                shell_cleaned.append(rc)

    # ------------------------------------------------------------------ #
    # 4) Final report                                                     #
    # ------------------------------------------------------------------ #
    if sys.platform == 'win32':
        exe_label  = "Removed ~/.hop2/bin from user PATH     "
        cfg_label  = "Cleaned PowerShell profile(s)          "
        reload_msg = "Please open a new PowerShell window to complete uninstallation."
        manual_msg = "  . $PROFILE"
    else:
        exe_label  = "Removed hop2 executable                "
        cfg_label  = "Cleaned shell config (.bashrc/.zshrc)  "
        reload_msg = "Please restart your shell to complete uninstallation."
        manual_msg = "    source ~/.hop2/init.sh"

    print("┌──────────────────────────────────────────╥────────┐")
    print("│ Action                                   ║ Status │")
    print("╞══════════════════════════════════════════╫════════╡")
    print(f"│ {exe_label} ║ {'✅' if removed_from else 'n/a'}    │")
    print(f"│ Removed ~/.hop2 data directory           ║ {'✅' if dir_removed else 'n/a'}    │")
    print(f"│ {cfg_label} ║ {'✅' if shell_cleaned else 'n/a'}    │")
    print("└──────────────────────────────────────────╨────────┘\n")

    if errors:
        print("⚠️  Some issues encountered:")
        for e in errors:
            print(f"  • {e}")
        print()

    print("✅ hop2 has been uninstalled.")
    if not shell_cleaned:
        print("⚠️  Manual cleanup required: remove the hop2 integration line")
        print(f"  {manual_msg}")
        print("  from your shell config.\n")

    print(reload_msg)
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
    if args.help:
        print_help()
        sys.exit(0)

    if args.uninstall:
        uninstall_me()
        sys.exit(0)

    if args.update:
        update_me()
        sys.exit(0)

    if args.backup:
        if args.backup is True:
            backup_data()
        else:
            backup_data(args.backup)
        sys.exit(0)

    if args.restore:
        restore_data(args.restore)
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