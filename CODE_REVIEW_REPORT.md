# hop2 — Code Review & Improvement Report

**Target audience:** an implementation agent (Sonnet). This document is self-contained: each task has a clear problem statement, the exact file/line location, the reason, and a concrete fix (usually with code). Apply the tasks in priority order. After applying, run the verification steps in the last section.

**Project summary:** `hop2` is a dependency-free Python 3 CLI (`hop2.py`) that stores directory and command aliases in a SQLite DB at `~/.hop2/hop2.db`. Shell wrapper functions (`init.sh` for bash/zsh, `init.ps1` for PowerShell) capture the CLI's stdout and intercept a magic `__HOP2_CD:<path>` string to change the caller's working directory. Installers are `install.sh` (Unix) and `install.ps1` (Windows).

**Files reviewed:** `hop2.py`, `init.sh`, `init.ps1`, `install.sh`, `install.ps1`, `README.md`, `.gitignore`.

---

## Severity legend

| Level | Meaning |
|-------|---------|
| 🔴 **Critical** | Breaks core functionality for real users right now. |
| 🟠 **High** | Significant bug or broken promise (docs, UX, cross-platform). |
| 🟡 **Medium** | Correctness/robustness issue that bites in edge cases. |
| 🟢 **Low** | Polish, consistency, maintainability. |

---

## Quick task checklist

- [ ] **T1** 🔴 Fix Windows emoji crash (UTF-8 stdout/stderr) — `hop2.py`, `init.ps1`
- [ ] **T2** 🟠 Command aliases capture output instead of streaming (no live output, no TTY, no color) — `init.sh`, `init.ps1`, `hop2.py`
- [ ] **T3** 🟠 README claims "Multi-Shell Support: bash and zsh" and a bash-only install, but Windows/PowerShell is fully supported — fix docs
- [ ] **T4** 🟠 Broken CI build badge (no `.github/workflows/ci.yml`) and no tests
- [ ] **T5** 🟡 `uses` counter increments even when the command errors out — `hop2.py`
- [ ] **T6** 🟡 Dead/inconsistent `go` and `update` subcommands vs. `known_subcommands` and completions
- [ ] **T7** 🟡 SQLite connections in `get_directory`/`get_command` are never closed — `hop2.py`
- [ ] **T8** 🟡 `hop2 add ls` (and other alias-shadowed names) silently become unreachable — `hop2.py`
- [ ] **T9** 🟢 `--backup` overwrites an existing file with no warning — `hop2.py`
- [ ] **T10** 🟢 Command aliases are shell-specific (a bash alias fails on Windows `cmd`) — document it
- [ ] **T11** 🟢 Code cleanup: duplicate `init_db`/`DB_DIR` creation, ugly SQL formatting, stale comments, variable shadowing
- [ ] **T12** 🟢 Add a `version`/`--version` flag and `pyproject.toml` for packaging

---

## 🔴 T1 — Windows emoji crash (the headline bug)

### Problem
Almost every command (`add`, `list`, `rm`, `cmd`, error messages) prints emoji (`✅ ❌ 📁 ⚡ 🌲 🗑️`). On a default Windows Python install the console/pipe encoding is **cp1252**, which cannot encode these characters.

The PowerShell wrapper in `init.ps1` **always captures stdout**:

```powershell
# init.ps1:40
$output = & $script:Hop2Python $script:Hop2Script @args
```

When stdout is a pipe (as it is here), Python uses the locale encoding (cp1252), so printing `✅` raises `UnicodeEncodeError` and the process crashes. The result: `hop2 add`, `hop2 list`, `hop2 rm`, and every emoji-bearing error are **broken on Windows** — the user sees a Python traceback, `$output` is empty, and the exit code is non-zero. (Directory jumps happen to survive only because `__HOP2_CD:<path>` contains no emoji.)

**Verified on this machine:**
```
stdout enc: cp1252
preferred: cp1252
$ python -c "print('✅')" | cat
UnicodeEncodeError: 'charmap' codec can't encode character '✅' ...
```

### Fix — two parts

**Part A — force UTF-8 output in `hop2.py`.** Add this immediately after the imports (top of the file, before any `print`):

```python
# Ensure emoji/Unicode output works even when stdout is a pipe on Windows
# (default cp1252 would raise UnicodeEncodeError). errors="replace" keeps us
# safe on consoles that still can't render a given glyph.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
```

> `io.TextIOWrapper.reconfigure` exists on Python 3.7+. The project targets Python 3, and Windows installs are ≥3.7 in practice, so this is safe. The `try/except` guards the rare non-reconfigurable stream.

**Part B — make PowerShell read that UTF-8 correctly in `init.ps1`.** Windows PowerShell 5.1 decodes captured process output using `[Console]::OutputEncoding` (often the OEM code page), so Python emitting UTF-8 bytes is not enough — PowerShell can still mangle them. Near the top of `init.ps1` (after the `$script:Hop2Python` detection block, ~line 17), add:

```powershell
# Make sure Python emits UTF-8 and PowerShell decodes captured output as UTF-8.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
```

> Setting `$env:PYTHONUTF8=1` is belt-and-suspenders with Part A (either alone fixes the crash; together they're robust across Python versions). The `[Console]::OutputEncoding` line is what makes the emoji render correctly rather than as mojibake.

### Acceptance
On Windows (PowerShell 5.1 and 7), `hop2 add work`, `hop2 list`, `hop2 rm work`, and a not-found alias all run without a traceback and show readable output.

---

## 🟠 T2 — Command aliases capture output instead of streaming

### Problem
Both shell wrappers capture the CLI's stdout to intercept `__HOP2_CD:`. But command aliases (`hop2 gs` → runs `git status`) are executed **inside** the captured Python process:

```python
# hop2.py:277
def run_command(alias, extra_args=None):
    cmd = get_command(alias)
    if cmd:
        full = f"{cmd} {' '.join(extra_args)}" if extra_args else cmd
        print(f"→ Running: {full}")
        subprocess.run(full, shell=True)   # inherits the captured stdout pipe
        return True
```

```bash
# init.sh:23
output=$(command hop2 "$@")   # captures EVERYTHING, including the subprocess
```

Consequences for every command alias:
1. **No live output** — the user sees nothing until the command finishes, then a dump.
2. **No colors** — tools detect a non-TTY stdout and disable color.
3. **Interactive/pager commands break** — `git log` (pager), anything prompting for input, progress bars, etc. hang or misbehave.
4. The `→ Running: ...` banner gets mixed into the captured blob.

This makes the "Command Aliases" feature — a headline feature in the README — significantly degraded.

### Fix — emit a "run this" directive and let the shell execute it in the real terminal

Change `run_command` so that, instead of executing the command itself, the CLI prints a second magic string and lets the shell wrapper run it with a live TTY. This mirrors the existing `__HOP2_CD:` design.

**In `hop2.py`:**

```python
def run_command(alias, extra_args=None):
    cmd = get_command(alias)
    if cmd:
        full = f"{cmd} {' '.join(extra_args)}" if extra_args else cmd
        # Let the calling shell run this so the command gets a real TTY
        # (live output, colors, pagers, prompts all work).
        print(f"__HOP2_RUN:{full}")
        return True
    return False
```

**In `init.sh`** (add a branch next to the `__HOP2_CD:` handling, ~line 27):

```bash
    if [[ $output == __HOP2_CD:* ]]; then
        local path="${output#__HOP2_CD:}"
        cd "$path" || return 1
    elif [[ $output == __HOP2_RUN:* ]]; then
        local runcmd="${output#__HOP2_RUN:}"
        eval "$runcmd"
    elif [ $exit_code -ne 0 ]; then
        ...
```

**In `init.ps1`** (add next to the `__HOP2_CD:` branch, ~line 46):

```powershell
    if ($outputStr -match '^__HOP2_CD:(.+)$') {
        ...
    } elseif ($outputStr -match '^__HOP2_RUN:(.+)$') {
        Invoke-Expression $Matches[1]
    } elseif ($exitCode -ne 0) {
        ...
```

> **Trade-off to note in the PR:** `eval`/`Invoke-Expression` runs a user-defined string in the user's own shell — this is exactly what an alias tool is supposed to do (the user authored the command), and it is strictly safer than today's `subprocess.run(shell=True)` only in the sense that it now runs in the correct shell context. Keep the `run_command` path gated to aliases the user created; do not feed untrusted input into it.
>
> If you prefer **not** to change the execution model, the minimum viable improvement is to stop capturing for command aliases — but the shell can't know an alias is a command vs. a directory without asking the CLI first, which is why the `__HOP2_RUN:` directive is the clean solution.

### Acceptance
`hop2 cmd gl "git log --oneline -5"` then `hop2 gl` shows colored, live git output; `hop2 cmd top htop` then `hop2 top` launches interactively.

---

## 🟠 T3 — README misrepresents platform support

### Problem
`README.md` says:

- Line 24: `**🐚 Multi-Shell Support:** Works seamlessly with bash and zsh.`
- Lines 31–42: installation shows only `curl -sL install.hop2.tech | bash` and `source ~/.bashrc` / `~/.zshrc`.

But the repo ships a **complete, careful Windows/PowerShell implementation** (`init.ps1`, `install.ps1`, Windows branches in `hop2.py` for uninstall, OneDrive-aware Documents lookup, HKCU PATH handling, PS 5.1 + 7 profiles). Windows users reading the README have no idea it's supported, and the only documented install is `bash`.

### Fix
Update `README.md`:

1. Change the feature bullet to include PowerShell/Windows:
   ```markdown
   -   **🐚 Multi-Shell Support:** Works with `bash`, `zsh`, and PowerShell (Windows, macOS, Linux).
   ```
2. Add a Windows installation section:
   ````markdown
   ### Windows (PowerShell)
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   iwr -useb https://install.hop2.tech/windows | iex
   ```
   Then reload your profile:
   ```powershell
   . $PROFILE
   ```
   ````
3. Note the cmd.exe limitation (see T10): directory jumping requires PowerShell; `cmd.exe` supports `add`/`list`/`rm`/`cmd` but not the `cd` hop.

---

## 🟠 T4 — Broken build badge + no tests

### Problem
`README.md:11` renders a GitHub Actions build badge pointing at `ci.yml`, but there is **no `.github/workflows/` directory** in the repo. The badge shows "no status"/broken, which undermines credibility. There are also **no tests**, making the refactors above risky.

### Fix
Add a minimal CI workflow and a small test suite.

**`.github/workflows/ci.yml`:**
```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.8', '3.11', '3.12']
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '${{ matrix.python-version }}' }
      - run: python -m pip install pytest
      - run: python -m pytest -q
```

**`tests/test_hop2.py`** — cover the pure logic by pointing `hop2` at a temp DB. Because `DB_PATH` is a module global computed at import, add a tiny hook so tests can override it, or `monkeypatch.setattr(hop2, "DB_PATH", tmp_db)` and call `hop2.init_db()`. Suggested cases:
- `add_directory` creates and then updates an alias; rejects reserved words; rejects nonexistent paths.
- `add_command` create/update.
- `get_directory`/`get_command` return values and increment `uses`.
- `remove_shortcut` for dir, command, and missing alias (check return codes 0/0/1).
- `backup_data` → `restore_data` round-trip (v2.0 format) and v1.0 flat-format parsing.
- **Regression for T1:** run `hop2.py add x` as a subprocess with `stdout=PIPE` and assert no `UnicodeEncodeError` (catches the Windows encoding bug on all platforms).

> Minor refactor to make testing clean: wrap the `DB_PATH` constants so they can be overridden via an env var, e.g. `DB_PATH = os.environ.get("HOP2_DB", os.path.expanduser("~/.hop2/hop2.db"))`. This also lets power users relocate their DB.

---

## 🟡 T5 — `uses` counter increments on error

### Problem
In `main()`, a directory alias increments `uses` via `get_directory`, but if the user also passed extra args (an error case) the increment has already happened:

```python
# hop2.py:709
path = get_directory(alias)          # <-- uses already incremented here
if path:
    if extra_args:
        print(f"❌ Directory shortcuts do not accept arguments. ...")
        sys.exit(1)                  # but we counted a "use"
    print(f"__HOP2_CD:{path}")
    sys.exit(0)
```

So a failed invocation inflates the usage stat that `list` sorts/ displays by.

### Fix
Split lookup from the increment, and only increment on the successful path. Simplest approach: add a `bump=True` parameter to `get_directory`, call it with `bump=False` for the initial lookup, and increment explicitly right before emitting `__HOP2_CD:`. Or reorder so the `extra_args` guard is checked before the lookup. Example:

```python
def get_directory(alias, bump=True):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT path FROM directories WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            if bump:
                c.execute("UPDATE directories SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row[0]
    return None
```
```python
path = get_directory(alias, bump=False)
if path:
    if extra_args:
        print("❌ Directory shortcuts do not accept arguments. ...")
        sys.exit(1)
    get_directory(alias)  # count the successful hop
    print(f"__HOP2_CD:{path}")
    sys.exit(0)
```
(Adjust to avoid the double query if you prefer — e.g. inline the UPDATE.) Apply the same reasoning to the command path if desired (currently command errors don't over-count because the increment and run are together).

---

## 🟡 T6 — Dead / inconsistent `go` and `update` subcommands

### Problem
There are three inconsistent lists of "commands":

- `RESERVED_ALIASES` (line 23) includes `'go'` and `'help'`.
- `known_subcommands = {'add', 'cmd', 'list', 'rm'}` (line 699) — **no `go`, no `update`**.
- The sub-parser defines an `update` subcommand (line 747) that is **unreachable** because `'update'` isn't in `known_subcommands`, so `hop2 update` is treated as an alias lookup instead.
- `init.sh` completion advertises `go` (line 61) and the zsh list omits it; `init.ps1` completion advertises neither `go` nor `update`.
- There is **no `go` implementation anywhere** — it's a reserved word and a completion entry that does nothing.

Net effect: `hop2 go` says "no shortcut found", `hop2 update` does an alias lookup (works only by accident if no alias named `update` exists — and actually falls through to "not found" because `update` is neither a dir nor command alias, so the `--update` flag is the only working path).

### Fix
Pick one consistent model. Recommended:
1. Drop `'go'` from `RESERVED_ALIASES` and from `init.sh` completion (or implement `hop2 go <alias>` as an explicit jump — but it's redundant with the bare-alias form, so removing is cleaner).
2. Either add `'update'` to `known_subcommands` so the `update` subparser is reachable, **or** remove the `update` subparser (line 747–748) since `--update` already exists. Removing is simplest.
3. Make completions match the real command set in both `init.sh` and `init.ps1`: `add cmd list ls rm --backup --restore --update --uninstall --help`.

---

## 🟡 T7 — Unclosed SQLite connections

### Problem
`get_directory` and `get_command` use `with sqlite3.connect(DB_PATH) as conn:`. For sqlite3, that context manager **commits but does not close** the connection. These run on the hot path (every jump / command lookup), leaking connection objects for the life of the process. It's short-lived per invocation so the impact is small, but on Windows an unclosed handle can also contribute to file-lock hiccups.

### Fix
Reuse the existing `get_conn()` context manager (lines 56–65), which both commits and closes:

```python
def get_directory(alias, bump=True):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT path FROM directories WHERE alias = ?", (alias,))
        row = c.fetchone()
        if row:
            if bump:
                c.execute("UPDATE directories SET uses = uses + 1 WHERE alias = ?", (alias,))
            return row[0]
    return None
```
Do the same for `get_command` and for the read in `list_all` (currently a raw `sqlite3.connect` that also isn't closed).

---

## 🟡 T8 — `hop2 add ls` (and similar) creates an unreachable alias

### Problem
`'ls'` is handled as an alias for `list` (line 695) but is **not** in `RESERVED_ALIASES`. A user can run `hop2 add ls` successfully, but `hop2 ls` will always route to `list`, so the shortcut is unreachable. Same applies to any future alias that collides with the `ls→list` remap. `'update'`/`'backup'`/`'restore'`/`'uninstall'` are likewise not reserved (they're only flags, but `hop2 add backup` then `hop2 backup` works as an alias — inconsistent with `--backup`).

### Fix
Add the shadowing names to `RESERVED_ALIASES`:
```python
RESERVED_ALIASES = [
    'add', 'cmd', 'list', 'ls', 'rm', 'go',
    'update', 'backup', 'restore', 'uninstall',
    'help', '--help', '-h',
]
```
(Keep `'go'` only if you implement it per T6; otherwise drop it there too.) This guarantees every created alias is reachable.

---

## 🟢 T9 — `--backup` silently overwrites an existing file

### Problem
`backup_data` (line 327) does `open(filename, 'w')` with no existence check. `hop2 --backup myfile.json` twice silently clobbers the first. The default timestamped name avoids this, but an explicit filename is a footgun.

### Fix
When an explicit filename is given and already exists, prompt before overwriting (mirroring the `restore` confirmation):
```python
if filename is not None and os.path.exists(filename):
    ans = input(f"⚠️  {filename} exists. Overwrite? [y/N]: ")
    if ans.lower() != 'y':
        print("❌ Backup cancelled.")
        return 1
```
(Thread the "was a filename explicitly passed" flag through, since `filename is None` currently means "use timestamp".)

---

## 🟢 T10 — Command aliases are inherently shell-specific

### Problem
A command alias stored on Linux (`find . -type f -printf '%s %p\n' | sort -nr | head`) will not run under Windows `cmd.exe`/PowerShell, and vice-versa. `run_command` uses `shell=True`, which is `cmd.exe` on Windows. The README's `bigfiles` example (line 78) is Unix-only. Backup/restore across platforms will carry non-portable commands.

### Fix
This is acceptable by design, but document it: add a note in the README's "Command Shortcuts" section that command aliases run in the native shell (bash/zsh on Unix, PowerShell/cmd on Windows) and are therefore platform-specific. Optionally, `list` could show a small hint. No code change required beyond docs.

---

## 🟢 T11 — Code cleanup (low-risk polish)

All in `hop2.py` unless noted:

1. **Duplicate directory creation:** both `init_db` (line 70) and `get_conn` (line 58) call `os.makedirs(DB_DIR, exist_ok=True)`. Keep it in `get_conn` (the single choke point) and have `init_db` use `get_conn`.
2. **SQL formatting:** the `CREATE TABLE` statements (lines 73–106) put every keyword on its own line (an IDE auto-format artifact). Collapse to readable one-column-per-line SQL.
3. **Stale comments:** lines 701–704 contain duplicated "In your main() function, update the alias-handling block" editing notes left in the source. Remove.
4. **Variable shadowing:** in `backup_data`, the local dict is named `backup_data`, shadowing the function (line 294). Rename to `payload`.
5. **`list_all` signature:** takes `_=None` and is called as `list_all()` from the subparser lambda — fine, but the unused param and the `conn.row_factory` comment (line 190) can be tidied; switch its raw connection to `get_conn`.
6. **Unused import:** confirm `shutil` (used in uninstall) and `tempfile` (used in update) are both still needed after refactors — they are; leave them.
7. **`print_help` exits with `sys.exit(0)` and is also followed by `sys.exit(0)` in `main` (lines 663–664, 687–688)** — redundant but harmless; optional cleanup.

---

## 🟢 T12 — Packaging & version

### Problem
There's no `--version`, no single source of truth for the version (README references `v1.0.0`, `backup_data` hardcodes `"version": "2.0"` for the *backup format*), and no `pyproject.toml` for `pip`/`pipx` installation as an alternative to the curl-pipe.

### Fix
1. Add `__version__ = "1.0.0"` near the top of `hop2.py` and a `--version` flag in `main()`'s argparse that prints it and exits.
2. (Optional, larger) Add a `pyproject.toml` with a `console_scripts` entry point so `pipx install hop2` works. Note that pip install alone won't wire up the shell function (the `cd` interception needs `init.sh`/`init.ps1`), so document that the shell integration still needs sourcing.

---

## Cross-platform review summary (Windows focus)

| Area | Status | Notes |
|------|--------|-------|
| Directory jump | ✅ works on PowerShell | `__HOP2_CD:` has no emoji, survives the T1 bug. |
| `add`/`list`/`rm`/`cmd` output | 🔴 **broken on default Windows Python** | T1 — emoji + cp1252 pipe → `UnicodeEncodeError`. **Fix first.** |
| Command aliases | 🟠 degraded (all platforms) | T2 — captured, no TTY. |
| `cmd.exe` support | ⚠️ partial by design | `hop2.bat` can't `cd` the parent shell; only PowerShell function can. Documented in installer. |
| Uninstall | ✅ solid | OneDrive-aware Documents, HKCU PATH, PS 5.1 + 7 profiles, Unix rc cleanup — well done. |
| Path handling | ✅ good | `commonpath` `ValueError` across drives is handled (line 204); `normcase` used for case-insensitive compare. |
| Install PATH | ✅ good | HKCU-only, no admin; updates current session. |
| Python detection | ✅ good | tries `python`/`python3`/`py`, checks `Python 3.`. |

**Bottom line for Windows:** the platform scaffolding (install/uninstall/path/profile) is genuinely well-built. The one thing standing between it and a working experience is the UTF-8/emoji crash (T1) — fixing that plus the docs (T3) makes Windows a first-class, advertised platform.

---

## Suggested implementation order

1. **T1** (unblocks Windows entirely) → verify with the command below.
2. **T7, T5, T6, T8** (small `hop2.py` correctness fixes, low risk).
3. **T2** (behavioral change to command aliases; touches all three of `hop2.py`/`init.sh`/`init.ps1`).
4. **T4** (CI + tests) — write tests against the now-fixed behavior.
5. **T3, T10, T9, T11, T12** (docs + polish).

---

## Verification steps (run after applying)

**Windows (PowerShell) — T1 regression:**
```powershell
python hop2.py add testdir
python hop2.py list
python hop2.py rm testdir
# None of these should print a Python traceback; emoji should render.
```

**Any platform — encoding regression (mimics the Windows pipe):**
```bash
python hop2.py list | cat    # must not raise UnicodeEncodeError
```

**Command alias streaming — T2:**
```bash
hop2 cmd gl "git log --oneline -5"
hop2 gl                      # should show live, colored git output
```

**Round-trip — T4/backup:**
```bash
hop2 --backup /tmp/b.json && hop2 --restore /tmp/b.json
```

**Tests:**
```bash
python -m pytest -q
```

---

## Appendix — file/line index of every issue

| Task | File | Line(s) |
|------|------|---------|
| T1 | `hop2.py` (add reconfigure) | after ~16 |
| T1 | `init.ps1` (capture + encoding) | 17, 40 |
| T2 | `hop2.py` `run_command` | 277–284 |
| T2 | `init.sh` capture/branch | 23, 27 |
| T2 | `init.ps1` capture/branch | 40, 46 |
| T3 | `README.md` | 24, 31–42 |
| T4 | (missing) `.github/workflows/ci.yml`, `tests/` | — |
| T4 badge | `README.md` | 11 |
| T5 | `hop2.py` `get_directory` / `main` | 165–173, 709–716 |
| T6 | `hop2.py` reserved/known/subparser | 23, 699, 747 |
| T6 | `init.sh` / `init.ps1` completions | 61, 79 |
| T7 | `hop2.py` `get_directory`/`get_command`/`list_all` | 165–184, 189 |
| T8 | `hop2.py` `RESERVED_ALIASES` | 23 |
| T9 | `hop2.py` `backup_data` | 287–336 |
| T10 | `README.md` / `hop2.py` `run_command` | 67–80, 277 |
| T11 | `hop2.py` various | 58, 70, 73–106, 190, 294, 701–704 |
| T12 | `hop2.py` / new `pyproject.toml` | top of file |
