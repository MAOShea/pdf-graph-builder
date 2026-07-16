# sync-corpse-plunder.ps1 — txt -> games/mork-borg/hand-authored-overrides/corpse-plunder-d66.json
$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
& $python "$PSScriptRoot\backend\sync_corpse_plunder.py" @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
