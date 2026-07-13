# install.ps1 — set up the pdf-graph-builder backend for Ollama-based ingest.
# Run from the backend folder:  .\install.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# ------------------------------------------------------------------
# 1. Find Python 3.11 or 3.12 via the py launcher
# ------------------------------------------------------------------
function Find-Python {
    foreach ($flag in @("-3.12", "-3.11")) {
        try {
            $ver = & py $flag --version 2>&1
            if ($ver -match "Python 3\.(1[12])") {
                return "py $flag"
            }
        } catch {}
    }
    # Fallback: try python3.12 / python3.11 directly on PATH
    foreach ($cmd in @("python3.12", "python3.11", "python")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python 3\.(1[12])") {
                return $cmd
            }
        } catch {}
    }
    return $null
}

$pythonCmd = Find-Python
if (-not $pythonCmd) {
    Write-Error "Python 3.11 or 3.12 is required but was not found.`nInstall it from https://www.python.org/downloads/ and re-run."
    exit 1
}

$pythonVer = & Invoke-Expression "$pythonCmd --version"
Write-Host "Using Python: $pythonCmd ($pythonVer)"

# ------------------------------------------------------------------
# 2. Create venv if it doesn't exist
# ------------------------------------------------------------------
$venvDir = Join-Path $PSScriptRoot "venv"

if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment at $venvDir ..."
    Invoke-Expression "$pythonCmd -m venv `"$venvDir`""
} else {
    Write-Host "Virtual environment already exists at $venvDir — reusing it."
}

# ------------------------------------------------------------------
# 3. Activate
# ------------------------------------------------------------------
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Could not find $activateScript — venv may not have been created correctly."
    exit 1
}
& $activateScript

Write-Host "Activated: $(python --version)"

# ------------------------------------------------------------------
# 4. Upgrade pip
# ------------------------------------------------------------------
python -m pip install --upgrade pip --quiet

# ------------------------------------------------------------------
# 5. Install dependencies
# ------------------------------------------------------------------
Write-Host "Installing dependencies from requirements-ollama.txt ..."
pip install -r requirements-ollama.txt

Write-Host ""
Write-Host "Done. To start the backend:"
Write-Host "  .\venv\Scripts\Activate.ps1"
Write-Host "  uvicorn score:app --reload"
