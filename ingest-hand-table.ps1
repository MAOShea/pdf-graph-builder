# ingest-hand-table.ps1 — ingest a hand-authored table JSON (no curl).
# Run from workspace root:
#   .\ingest-hand-table.ps1
#   .\ingest-hand-table.ps1 -JsonPath .\mork-borg-corpse-plunder-d66.json

param(
    [string]$JsonPath = "$PSScriptRoot\mork-borg-corpse-plunder-d66.json",
    [string]$Document = "mork-borg.pdf"
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"

if (-not (Test-Path $JsonPath)) {
    Write-Error "JSON not found: $JsonPath"
    exit 1
}

Write-Host "Ingesting hand-authored table: $JsonPath"
& $python "$PSScriptRoot\backend\ingest_hand_table.py" $JsonPath --document $Document
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done."
