#Requires -Version 5.0
# hop2 Windows installer — no administrator rights required
#
# Quick install (PowerShell):
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   iex ((New-Object System.Net.WebClient).DownloadString('https://install.hop2.tech/windows'))
#
# Or if you already have a relaxed execution policy:
#   iwr -useb https://install.hop2.tech/windows | iex

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "         (\_/)           HOP2 Installer" -ForegroundColor Cyan
Write-Host "         ( *_*)  /-----------------\     /------------------\" -ForegroundColor Cyan
Write-Host "        / >  <   HOP FROM...   >   <   ...TO HERE!    >" -ForegroundColor Cyan
Write-Host "                 \_________________/     \______HOP2_______/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installing hop2 for Windows (no admin required)..." -ForegroundColor Green
Write-Host ""

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Find-Python3 {
    foreach ($cmd in @('python', 'python3', 'py')) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) {
            $ver = & $cmd --version 2>&1
            if ($ver -match 'Python 3\.') {
                return $cmd
            }
        }
    }
    return $null
}

function Add-DirToUserPath {
    param([string]$Dir)
    # Read current user PATH (HKCU, never touches HKLM so no admin needed)
    $currentPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    $parts = if ($currentPath) { $currentPath -split ';' | Where-Object { $_ -ne '' } } else { @() }
    if ($parts -notcontains $Dir) {
        $newPath = ($parts + $Dir) -join ';'
        [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User')
        # Also update the current session so hop2.bat is usable right away
        $env:PATH = "$env:PATH;$Dir"
        return $true
    }
    return $false
}

function Add-ToProfile {
    param(
        [string]$ProfilePath,
        [string]$SourceLine,
        [string]$Comment
    )
    $dir = Split-Path $ProfilePath -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    if (-not (Test-Path $ProfilePath)) {
        New-Item -ItemType File -Path $ProfilePath -Force | Out-Null
    }
    $existing = Get-Content $ProfilePath -Raw -ErrorAction SilentlyContinue
    if (-not $existing -or $existing -notlike "*$SourceLine*") {
        Add-Content -Path $ProfilePath -Value ""
        Add-Content -Path $ProfilePath -Value $Comment
        Add-Content -Path $ProfilePath -Value $SourceLine
        return $true
    }
    return $false   # already present
}

function Get-PSProfilePaths {
    # Returns candidate profile paths for both Windows PowerShell 5.1 and PowerShell 7+
    $docs = [Environment]::GetFolderPath('MyDocuments')
    return @(
        # Windows PowerShell 5.1
        (Join-Path $docs 'WindowsPowerShell\Microsoft.PowerShell_profile.ps1'),
        # PowerShell 7+
        (Join-Path $docs 'PowerShell\Microsoft.PowerShell_profile.ps1')
    )
}

# ---------------------------------------------------------------------------
# 1. Check for Python 3
# ---------------------------------------------------------------------------
Write-Host "  [1/6] Checking for Python 3..." -NoNewline
$python = Find-Python3
if (-not $python) {
    Write-Host " NOT FOUND" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Python 3 is required. Please install it from https://python.org" -ForegroundColor Red
    Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    exit 1
}
$pyVersion = (& $python --version 2>&1)
Write-Host " $pyVersion" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 2. Create hop2 home directory
# ---------------------------------------------------------------------------
$hop2Dir = Join-Path $HOME '.hop2'
$hop2Bin = Join-Path $hop2Dir 'bin'
Write-Host "  [2/6] Creating $hop2Dir..." -NoNewline
New-Item -ItemType Directory -Path $hop2Dir -Force | Out-Null
New-Item -ItemType Directory -Path $hop2Bin  -Force | Out-Null
Write-Host " Done" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 3. Download hop2.py and init.ps1
# ---------------------------------------------------------------------------
$baseUrl  = 'https://raw.githubusercontent.com/vishukamble/hop2/main'
$pyDest   = Join-Path $hop2Dir 'hop2.py'
$initDest = Join-Path $hop2Dir 'init.ps1'

Write-Host "  [3/6] Downloading hop2 files..."
try {
    # -UseBasicParsing avoids dependency on Internet Explorer engine (needed on Server / minimal installs)
    Invoke-WebRequest -Uri "$baseUrl/hop2.py"   -OutFile $pyDest   -UseBasicParsing
    Write-Host "         hop2.py   -> $pyDest" -ForegroundColor Green
    Invoke-WebRequest -Uri "$baseUrl/init.ps1"  -OutFile $initDest -UseBasicParsing
    Write-Host "         init.ps1  -> $initDest" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "  Download failed: $_" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# 4. Create thin wrappers in ~/.hop2/bin
# ---------------------------------------------------------------------------
Write-Host "  [4/6] Creating command wrappers in $hop2Bin..."

# hop2.bat — lets hop2 work from cmd.exe (directory-change not supported there,
# but all other operations like add/list/rm/cmd work fine)
# Uses whichever Python command was detected during installation.
$batContent = @"
@echo off
$python "%USERPROFILE%\.hop2\hop2.py" %*
"@
Set-Content -Path (Join-Path $hop2Bin 'hop2.bat') -Value $batContent -Encoding ASCII

# hop2.ps1 — thin wrapper for calling hop2 as a script (not as a function)
#            Note: this does NOT support directory changes; use init.ps1 for full PS support.
$ps1WrapperContent = "& $python `"$pyDest`" @args"
Set-Content -Path (Join-Path $hop2Bin 'hop2.ps1') -Value $ps1WrapperContent -Encoding UTF8

Write-Host "         hop2.bat  (cmd.exe)" -ForegroundColor Green
Write-Host "         hop2.ps1  (PowerShell script wrapper)" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 5. Add ~/.hop2/bin to user PATH (no admin — HKCU only)
# ---------------------------------------------------------------------------
Write-Host "  [5/6] Adding $hop2Bin to user PATH..." -NoNewline
$added = Add-DirToUserPath $hop2Bin
if ($added) {
    Write-Host " Done" -ForegroundColor Green
} else {
    Write-Host " Already present" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 6. PowerShell profile integration
# ---------------------------------------------------------------------------
Write-Host "  [6/6] Configuring PowerShell profiles..."

# Set execution policy to RemoteSigned for the current user so that
# init.ps1 (downloaded from the internet) can be dot-sourced.
# This scope does NOT require admin rights.
$policy = Get-ExecutionPolicy -Scope CurrentUser
if ($policy -in @('Undefined', 'Restricted')) {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    Write-Host "         Execution policy set to RemoteSigned for current user." -ForegroundColor Green
}

# Unblock downloaded files (marks them as trusted even if downloaded from the internet)
if (Get-Command Unblock-File -ErrorAction SilentlyContinue) {
    Unblock-File -Path $initDest -ErrorAction SilentlyContinue
    Unblock-File -Path $pyDest  -ErrorAction SilentlyContinue
}

$sourceLine = ". `"$initDest`""
$comment    = "# hop2 shell integration"

$profilePaths  = Get-PSProfilePaths
$updatedProfiles = @()

foreach ($profilePath in $profilePaths) {
    $psName = if ($profilePath -like '*WindowsPowerShell*') { 'Windows PowerShell 5.1' } else { 'PowerShell 7+' }
    Write-Host "         $psName profile: $profilePath" -NoNewline

    $wasAdded = Add-ToProfile -ProfilePath $profilePath -SourceLine $sourceLine -Comment $comment
    if ($wasAdded) {
        Write-Host " -> Added" -ForegroundColor Green
        $updatedProfiles += $profilePath
    } else {
        Write-Host " -> Already configured" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Done — print quick-start guide
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "  hop2 installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "+----------------------------------+------------------------------------------+" -ForegroundColor Cyan
Write-Host "| Command                          | What it does                             |" -ForegroundColor Cyan
Write-Host "+----------------------------------+------------------------------------------+" -ForegroundColor Cyan
Write-Host "| hop2 add work                    | Add current directory as 'work'          |" -ForegroundColor Cyan
Write-Host "| hop2 work                        | Jump to that directory                   |" -ForegroundColor Cyan
Write-Host "| hop2 cmd gs 'git status'         | Create command alias 'gs'                |" -ForegroundColor Cyan
Write-Host "| hop2 gs                          | Run 'git status'                         |" -ForegroundColor Cyan
Write-Host "| h work                           | Use 'h' for shorter directory jumps      |" -ForegroundColor Cyan
Write-Host "| hop2 --backup                    | Backup shortcuts to timestamped JSON     |" -ForegroundColor Cyan
Write-Host "| hop2 --restore backup.json       | Restore shortcuts from backup file       |" -ForegroundColor Cyan
Write-Host "+----------------------------------+------------------------------------------+" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Final step: reload your PowerShell profile to activate hop2:" -ForegroundColor Yellow
Write-Host ""
Write-Host "      . `$PROFILE" -ForegroundColor White
Write-Host ""
Write-Host "  (Or just open a new PowerShell window.)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  To remove hop2 later:  hop2 --uninstall" -ForegroundColor DarkGray
Write-Host ""
