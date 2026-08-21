# pdf-as-md.ps1 — runtime PDF read path → Markdown (no Neo4j)
# Run from anywhere; uses backend\venv.
param(
    [string]$Game = "mork-borg",
    [string]$FileName = "mork-borg.pdf",
    [string]$Pdf = "",
    [string[]]$Section = @(),  # focused dump: clip to these ids; skip CREATURES appendix
    [string]$Output = "",
    [switch]$PagesOnly,
    [switch]$SectionsOnly,
    [switch]$NoEntities
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$repo = Resolve-Path (Join-Path $here "..\..")
$python = Join-Path $repo "backend\venv\Scripts\python.exe"
$script = Join-Path $here "pdf_as_md.py"

if (-not (Test-Path $python)) {
    throw "Backend venv not found: $python"
}

$argsList = @(
    $script,
    "--game", $Game,
    "--file-name", $FileName
)
if ($Pdf) { $argsList += @("--pdf", $Pdf) }
foreach ($raw in $Section) {
    foreach ($part in ($raw -split ",")) {
        $sid = $part.Trim()
        if ($sid) { $argsList += @("--section", $sid) }
    }
}
if ($Output) { $argsList += @("-o", $Output) }
if ($PagesOnly) { $argsList += "--pages-only" }
if ($SectionsOnly) { $argsList += "--sections-only" }
if ($NoEntities) { $argsList += "--no-entities" }

& $python @argsList
exit $LASTEXITCODE
