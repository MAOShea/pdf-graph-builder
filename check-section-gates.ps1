# check-section-gates.ps1 — contract-driven section / index / spine ingest gates.
# Run from workspace root after ingest: .\check-section-gates.ps1
# Fail closed. Table coverage is .\check-coverage.ps1 (separate).

param(
    [string]$Game = "mork-borg",
    [string]$Document = "mork-borg.pdf",
    [int]$Phase = 2,
    [string]$Column = "RULES",
    [switch]$Verbose,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\check_section_gates.py"

$pyArgs = @($script, "--game", $Game, "--document", $Document, "--phase", $Phase, "--column", $Column)
if ($Verbose) { $pyArgs += "--verbose" }
if ($Json) { $pyArgs += "--json" }

& $python @pyArgs
exit $LASTEXITCODE
