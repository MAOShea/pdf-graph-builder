# materialize-rulebook-index.ps1 — p.75 index catalog + fiction instances (Briefings 7+8).
# Run from workspace root: .\materialize-rulebook-index.ps1

param(
    [string]$Document = "mork-borg.pdf",
    [string]$Game = "mork-borg",
    [int]$Phase = 0,
    [switch]$NoSections,
    [switch]$NoFiction
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\materialize_rulebook_index.py"

$args = @($script, "--document", $Document, "--game", $Game)
if ($Phase -gt 0) { $args += @("--phase", $Phase) }
if ($NoSections) { $args += "--no-sections" }
if ($NoFiction) { $args += "--no-fiction" }

& $python @args
exit $LASTEXITCODE
