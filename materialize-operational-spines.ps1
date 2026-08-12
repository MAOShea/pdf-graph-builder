# materialize-operational-spines.ps1 — altitude-D If spines (Briefing 17 / D1).
# Run from workspace root:
#   .\materialize-operational-spines.ps1
#   .\materialize-operational-spines.ps1 -EnsureSections

param(
    [string]$Document = "mork-borg.pdf",
    [string]$Game = "mork-borg",
    [int]$SectionPhase = 2,
    [switch]$EnsureSections
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\materialize_operational_spines.py"

$args = @($script, "--document", $Document, "--game", $Game, "--section-phase", $SectionPhase)
if ($EnsureSections) { $args += "--ensure-sections" }

& $python @args
exit $LASTEXITCODE
