# ingest-tables.ps1 — Materialize manifest lookup tables from PDF (CLI, no HTTP).
# Requires Neo4j credentials in backend/.env.
#
# Examples:
#   .\ingest-tables.ps1
#   .\ingest-tables.ps1 -PdfPath .\mork-borg.pdf -Tables WeaponTable,ArmorTable
#   .\ingest-tables.ps1 -StartPage 4 -EndPage 5

param(
    [string]$PdfPath = "",
    [string]$Document = "mork-borg.pdf",
    [string]$Game = "mork-borg",
    [string[]]$Tables = @(),
    [int]$StartPage = 0,
    [int]$EndPage = 0,
    [switch]$NoHandAuthored,
    [switch]$NoBundles
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\ingest_tables.py"

$args = @($script, "--document", $Document, "--game", $Game)
if ($PdfPath) { $args += @("--pdf", $PdfPath) }
if ($Tables.Count -gt 0) { $args += @("--tables") + $Tables }
if ($StartPage -gt 0) { $args += @("--start-page", $StartPage) }
if ($EndPage -gt 0) { $args += @("--end-page", $EndPage) }
if ($NoHandAuthored) { $args += "--no-hand-authored" }
if ($NoBundles) { $args += "--no-bundles" }

& $python @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
