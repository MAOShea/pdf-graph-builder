# ingest-morkborg.ps1 — upload and extract the Mork Borg PDF into the morkborg Neo4j DB.
# Run from the workspace root: .\ingest-morkborg.ps1

$ErrorActionPreference = "Stop"
$BackendUrl = "http://localhost:8000"
$PdfPath    = "$PSScriptRoot\mork-borg.pdf"
$FileName   = "mork-borg.pdf"
$Model      = "ollama_llama3"
$Uri        = "neo4j://127.0.0.1:7687"
$User       = "neo4j"
$Password   = "69696969"
$Database   = "morkborg"

if (-not (Test-Path $PdfPath)) {
    Write-Error "PDF not found at $PdfPath — make sure mork-borg.pdf is in the workspace root."
    exit 1
}

# ------------------------------------------------------------------
# 0. Pre-ingest cleanup — clear all ingest-created data, leave scaffold intact
# ------------------------------------------------------------------
Write-Host "Clearing previous ingest data (IngestNode, OVERRIDES_SEED, FlaggedRelationship, FlaggedConcept) ..."
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
& $python -c @"
from neo4j import GraphDatabase
driver = GraphDatabase.driver('$Uri', auth=('$User', '$Password'))
with driver.session(database='$Database') as s:
    s.run('MATCH ()-[r:OVERRIDES_SEED]->() DELETE r')
    s.run('MATCH (n:IngestNode) DETACH DELETE n')
    s.run('MATCH (n:FlaggedRelationship) DETACH DELETE n')
    s.run('MATCH (n:FlaggedConcept) DETACH DELETE n')
    print('Cleanup done.')
driver.close()
"@

# ------------------------------------------------------------------
# 1. Upload
# ------------------------------------------------------------------
Write-Host "Uploading $FileName ..."
$uploadResponse = curl.exe -s -X POST "$BackendUrl/upload" `
    -F "file=@$PdfPath;type=application/pdf" `
    -F "originalname=$FileName" `
    -F "chunkNumber=1" `
    -F "totalChunks=1" `
    -F "model=$Model" `
    -F "uri=$Uri" `
    -F "userName=$User" `
    -F "password=$Password" `
    -F "database=$Database"

Write-Host "Upload response: $uploadResponse"

# ------------------------------------------------------------------
# 2. Extract (scaffold-diff mode)
# ------------------------------------------------------------------
Write-Host ""
Write-Host "Starting scaffold-diff extraction — this will take a while ..."
$extractResponse = curl.exe -s -X POST "$BackendUrl/extract" `
    -F "file_name=$FileName" `
    -F "source_type=local file" `
    -F "model=$Model" `
    -F "ingest_mode=scaffold-diff" `
    -F "token_chunk_size=512" `
    -F "chunk_overlap=100" `
    -F "chunks_to_combine=1" `
    -F "uri=$Uri" `
    -F "userName=$User" `
    -F "password=$Password" `
    -F "database=$Database"

Write-Host "Extract response: $extractResponse"
