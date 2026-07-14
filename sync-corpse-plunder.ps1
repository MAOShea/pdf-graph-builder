# sync-corpse-plunder.ps1 — txt (double-space columns) -> JSON beside mork-borg.pdf
$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
& $python "$PSScriptRoot\backend\sync_corpse_plunder.py" @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
