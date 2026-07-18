# check-coverage.ps1 — manifest-driven ingest coverage report.
# Run from workspace root: .\check-coverage.ps1

param(
    [string]$Game = "mork-borg",
    [string]$Document = "mork-borg.pdf",
    [int]$Phase = 0,
    [switch]$Verbose,
    [switch]$Json,
    [switch]$ValidateAcceptance
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\check_coverage.py"

$args = @($script, "--game", $Game, "--document", $Document)
if ($Phase -gt 0) { $args += @("--phase", $Phase) }
if ($Verbose) { $args += "--verbose" }
if ($Json) { $args += "--json" }
if ($ValidateAcceptance) { $args += "--validate-acceptance" }

& $python @args
exit $LASTEXITCODE
