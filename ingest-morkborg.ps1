# ingest-morkborg.ps1 — Mörk Borg PDF ingest (wrapper around ingest-pdf.ps1).
# Run from the workspace root:
#   .\ingest-morkborg.ps1
#   .\ingest-morkborg.ps1 -SectionPhase 2
#   .\ingest-morkborg.ps1 -StartPage 27 -EndPage 31
#
# After ingest: .\check-section-gates.ps1 then .\check-coverage.ps1
#
# -SectionPhase: ingest filter = coverage phase (ADA DESIGN §4.5.1). Inclusive max:
#   1 = tests/DR/HP only (no spines/sheets); 2 = default (WORLD + combat/powers + spines);
#   3 = optional tables too. Not a slice id (2a–2g). Backend /extract omit still defaults to 1.

param(
    [int]$StartPage = 0,
    [int]$EndPage = 0,
    [int]$SectionPhase = 2
)

$invokeArgs = @{
    PdfPath       = "$PSScriptRoot\mork-borg.pdf"
    Cleanup       = $true
    SectionPhase  = $SectionPhase
}
if ($StartPage -gt 0) { $invokeArgs.StartPage = $StartPage }
if ($EndPage -gt 0) { $invokeArgs.EndPage = $EndPage }

& "$PSScriptRoot\ingest-pdf.ps1" @invokeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
