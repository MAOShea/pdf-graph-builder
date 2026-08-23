# check-content-remainder.ps1 — contract section spans vs PDF stream leftovers.
# Run from workspace root: .\check-content-remainder.ps1
# No Neo4j. Fail closed on unclassified gaps ≥ --MinChars.
# Table coverage: .\check-coverage.ps1. Section shape: .\check-section-gates.ps1.

param(
    [string]$Game = "mork-borg",
    [string]$Document = "mork-borg.pdf",
    [int]$Phase = 0,
    [int]$MinChars = 40,
    [switch]$Verbose,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\check_content_remainder.py"

$pyArgs = @($script, "--game", $Game, "--document", $Document, "--min-chars", $MinChars)
if ($Phase -gt 0) { $pyArgs += @("--phase", $Phase) }
if ($Verbose) { $pyArgs += "--verbose" }
if ($Json) { $pyArgs += "--json" }

& $python @pyArgs
exit $LASTEXITCODE
