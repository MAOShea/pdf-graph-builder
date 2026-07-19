# materialize-passage-sections.ps1 — heading-anchor section chunks (Briefing 6).
# Run from workspace root: .\materialize-passage-sections.ps1

param(
    [string]$Document = "mork-borg.pdf",
    [string]$Game = "mork-borg",
    [int]$Phase = 1,
    [switch]$StrictPhase
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\materialize_passage_sections.py"

$args = @($script, "--document", $Document, "--game", $Game, "--phase", $Phase)
if ($StrictPhase) { $args += "--strict-phase" }

& $python @args
exit $LASTEXITCODE
