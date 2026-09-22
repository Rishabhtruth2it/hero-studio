# Installs (first run) and launches Hero Studio. Invoked by "Launch Hero Studio.bat".
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

Write-Host "=== Hero Studio ==="

function Find-Python311 {
    foreach ($cand in @("python3.11", "python3.12", "python3.13", "python")) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if ($cmd) {
            $verOut = & $cmd.Source -c "import sys; print(sys.version_info[0], sys.version_info[1])" 2>$null
            if ($verOut) {
                $parts = $verOut -split " "
                if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11) {
                    return $cmd.Source
                }
            }
        }
    }
    return $null
}

$pybin = Find-Python311

if (-not $pybin) {
    Write-Host "No Python 3.11+ found. Installing one locally via uv (no admin needed)..."
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Invoke-Expression (Invoke-RestMethod https://astral.sh/uv/install.ps1)
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    }
    uv python install 3.11
    $pybin = (uv python find 3.11)
}

Write-Host "Using Python: $pybin"

$venvPython = ".\.venv\Scripts\python.exe"

if (-not (Test-Path ".venv")) {
    Write-Host "First run: setting up (this takes a few minutes)..."
    & $pybin -m venv .venv
    & $venvPython -m pip install --upgrade pip -q
    & $venvPython -m pip install -r requirements.txt -q
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env - add your Runway/Kling/OpenAI API key from the Settings tab once the app opens."
}

& $venvPython -m webapp.server
