# ingest-morkborg.ps1 — Mörk Borg PDF ingest (wrapper around ingest-pdf.ps1).
# Run from the workspace root:
#   .\ingest-morkborg.ps1
#   .\ingest-morkborg.ps1 -SectionPhase 2
#   .\ingest-morkborg.ps1 -StartPage 27 -EndPage 31
#
# After ingest: .\check-section-gates.ps1 then .\check-coverage.ps1
#
# -SectionPhase: max passage-sections.json phase (inclusive). Default 2 = RULES
# phase-1 + THE WORLD (Briefing 13). Use 1 for phase-1 only; 3 for later RULES.

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
