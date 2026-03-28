# hop2 PowerShell integration
# Add this to your PowerShell profile ($PROFILE):
#   . "$HOME\.hop2\init.ps1"

$script:Hop2Script = Join-Path $HOME '.hop2\hop2.py'

# Detect Python 3 executable once at load time
$script:Hop2Python = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $ver = & $candidate --version 2>&1
        if ($ver -match 'Python 3\.') {
            $script:Hop2Python = $candidate
            break
        }
    }
}

# ---------------------------------------------------------------------------
# Main hop2 function
# ---------------------------------------------------------------------------
function hop2 {
    if (-not $script:Hop2Python) {
        Write-Error "hop2: Python 3 not found. Please install Python 3 from https://python.org"
        return 1
    }

    if ($args.Count -eq 0) {
        & $script:Hop2Python $script:Hop2Script --help
        return
    }

    # Commands that need interactive stdin must run without output capture
    if ($args[0] -in @('--uninstall', '--update', '--restore', '--backup')) {
        & $script:Hop2Python $script:Hop2Script @args
        return $LASTEXITCODE
    }

    # Capture output so we can intercept the __HOP2_CD: magic string
    $output = & $script:Hop2Python $script:Hop2Script @args
    $exitCode = $LASTEXITCODE

    # Normalise: Python may return a string or an array of strings
    $outputStr = if ($output -is [array]) { $output -join "`n" } else { [string]$output }

    if ($outputStr -match '^__HOP2_CD:(.+)$') {
        $targetPath = $Matches[1].Trim()
        if (Test-Path $targetPath -PathType Container) {
            Set-Location $targetPath
        } else {
            Write-Error "hop2: Directory not found: $targetPath"
            return 1
        }
    } elseif ($exitCode -ne 0) {
        if ($outputStr) { Write-Host $outputStr -ForegroundColor Red }
        return $exitCode
    } elseif ($outputStr) {
        Write-Output $outputStr
    }
}

# ---------------------------------------------------------------------------
# Short alias 'h'
# ---------------------------------------------------------------------------
function h {
    if ($args.Count -eq 0) {
        hop2 list
    } else {
        hop2 @args
    }
}

# ---------------------------------------------------------------------------
# Tab completion for hop2 and h
# ---------------------------------------------------------------------------
Register-ArgumentCompleter -CommandName @('hop2', 'h') -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $builtins = @(
        'add', 'cmd', 'list', 'ls', 'rm',
        '--backup', '--restore', '--update', '--uninstall', '--help'
    )

    $dbPath = Join-Path $HOME '.hop2\hop2.db'
    $userAliases = @()

    if (Test-Path $dbPath) {
        try {
            # Detect Python (can't rely on module-scope variable inside ScriptBlock)
            $pyExe = @('python', 'python3', 'py') |
                     Where-Object { Get-Command $_ -ErrorAction SilentlyContinue } |
                     Select-Object -First 1

            if ($pyExe) {
                # Pass the DB path as sys.argv[1] to avoid quoting/injection issues
                $pyCode = "import sqlite3,sys; conn = sqlite3.connect(sys.argv[1]); c = conn.cursor(); c.execute('SELECT alias FROM directories UNION SELECT alias FROM commands'); [print(r[0]) for r in c.fetchall()]; conn.close()"
                $result = & $pyExe -c $pyCode $dbPath 2>$null
                if ($result) {
                    # .Trim() strips any trailing \r left over from Python's \r\n on Windows
                    $userAliases = @($result | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
                }
            }
        } catch {}
    }

    ($builtins + $userAliases) |
        Where-Object { $_ -like "$wordToComplete*" } |
        ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
}
