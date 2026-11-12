# Canada Immigration Agent: installer for Windows.
# Right-click > Run with PowerShell, or in PowerShell:  powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$py = $null
foreach ($name in @("python3", "python", "py")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) {
        $out = & $cmd.Source --version 2>$null
        if ($out -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 10) { $py = $cmd.Source; break }
    }
}
if (-not $py) {
    Write-Host "Python 3.10 or newer was not found."
    Write-Host "Install Python from the Microsoft Store (search 'Python 3.12'), then run this installer again."
    exit 1
}

Write-Host "Installing the Python libraries..."
& $py -m pip install --user --upgrade pip | Out-Null
& $py -m pip install --user -r requirements.txt
Write-Host ""
& $py scripts/setup_check.py --install
exit $LASTEXITCODE
