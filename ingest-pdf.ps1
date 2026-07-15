# ingest-pdf.ps1 — PDF ingest via backend API (Python CLI, no curl).
# Requires backend running: .\start.ps1
#
# Examples:
#   .\ingest-pdf.ps1
#   .\ingest-pdf.ps1 -StartPage 27 -EndPage 31
#   .\ingest-pdf.ps1 -PdfPath .\mork-borg.pdf -AdditionalInstructions "Extract RulePassage nodes..."

param(
    [string]$PdfPath = "$PSScriptRoot\mork-borg.pdf",
    [int]$StartPage = 0,
    [int]$EndPage = 0,
    [string]$BackendUrl = "http://localhost:8000",
    [string]$Model = "ollama_llama3",
    [string]$IngestMode = "scaffold-diff",
    [string]$AdditionalInstructions = "",
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
$script = "$PSScriptRoot\backend\ingest_pdf.py"

$args = @(
    $script,
    $PdfPath,
    "--backend-url", $BackendUrl,
    "--model", $Model,
    "--ingest-mode", $IngestMode
)
if ($Cleanup) { $args += "--cleanup" }
if ($StartPage -gt 0) { $args += @("--start-page", $StartPage) }
if ($EndPage -gt 0) { $args += @("--end-page", $EndPage) }
if ($AdditionalInstructions) { $args += @("--additional-instructions", $AdditionalInstructions) }

& $python @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
