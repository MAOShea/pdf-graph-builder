# ingest-morkborg.ps1 — Mörk Borg PDF ingest (wrapper around ingest-pdf.ps1).
# Run from the workspace root:
#   .\ingest-morkborg.ps1
#   .\ingest-morkborg.ps1 -StartPage 27 -EndPage 31

param(
    [int]$StartPage = 0,
    [int]$EndPage = 0
)

$invokeArgs = @{
    PdfPath  = "$PSScriptRoot\mork-borg.pdf"
    Cleanup  = $true
}
if ($StartPage -gt 0) { $invokeArgs.StartPage = $StartPage }
if ($EndPage -gt 0) { $invokeArgs.EndPage = $EndPage }

& "$PSScriptRoot\ingest-pdf.ps1" @invokeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
