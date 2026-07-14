# ingest-morkborg-json.ps1 — ingest hand-authored structured JSON rulebook sections.
# Run from the workspace root: .\ingest-morkborg-json.ps1
#
# Each .json file under corpus/mork-borg/ becomes one Document; each block = one atomic Chunk.
# See docs/structured-ingest-schema.md

$ErrorActionPreference = "Stop"
$BackendUrl = "http://localhost:8000"
$CorpusDir  = "$PSScriptRoot\corpus\mork-borg"
$Model      = "ollama_llama3"
$Uri        = "neo4j://127.0.0.1:7687"
$User       = "neo4j"
$Password   = "69696969"
$Database   = "morkborg"

$JsonFiles = Get-ChildItem -Path $CorpusDir -Filter "*.json" -Recurse | Sort-Object FullName
if ($JsonFiles.Count -eq 0) {
    Write-Error "No JSON files found under $CorpusDir"
    exit 1
}

Write-Host "Found $($JsonFiles.Count) structured JSON file(s) under corpus/mork-borg/"

# ------------------------------------------------------------------
# 0. Pre-ingest cleanup — clear ingest data + old documents/chunks; keep scaffold
# ------------------------------------------------------------------
Write-Host "Clearing previous ingest data (Documents, Chunks, IngestNodes, flags) ..."
$python = "$PSScriptRoot\backend\venv\Scripts\python.exe"
& $python -c @"
from neo4j import GraphDatabase
driver = GraphDatabase.driver('$Uri', auth=('$User', '$Password'))
with driver.session(database='$Database') as s:
    s.run('MATCH ()-[r:OVERRIDES_SEED|POSSIBLE_OVERRIDES_SEED|CONFIRMS_SEED|DOCUMENTED_BY|INSTANCE_OF|REFERENCES|HAS_COLUMN|HAS_ENTRY|APPLIES_TO|USES]->() DELETE r')
    s.run('MATCH (n:IngestNode) DETACH DELETE n')
    s.run('MATCH (n:FlaggedRelationship) DETACH DELETE n')
    s.run('MATCH (n:FlaggedConcept) DETACH DELETE n')
    s.run('MATCH (c:Chunk) DETACH DELETE c')
    s.run('MATCH (d:Document) DETACH DELETE d')
    print('Cleanup done.')
driver.close()
"@

foreach ($file in $JsonFiles) {
    $FileName = $file.Name
    $FilePath = $file.FullName
    Write-Host ""
    Write-Host "=== $FileName ==="

    # Upload
    Write-Host "Uploading ..."
    $uploadResponse = curl.exe -s -X POST "$BackendUrl/upload" `
        -F "file=@$FilePath;type=application/json" `
        -F "originalname=$FileName" `
        -F "chunkNumber=1" `
        -F "totalChunks=1" `
        -F "model=$Model" `
        -F "uri=$Uri" `
        -F "userName=$User" `
        -F "password=$Password" `
        -F "database=$Database"
    Write-Host "Upload: $uploadResponse"

    # Extract (scaffold-diff)
    Write-Host "Extracting (scaffold-diff) ..."
    $extractResponse = curl.exe -s -X POST "$BackendUrl/extract" `
        -F "file_name=$FileName" `
        -F "source_type=local file" `
        -F "model=$Model" `
        -F "ingest_mode=scaffold-diff" `
        -F "chunks_to_combine=1" `
        -F "uri=$Uri" `
        -F "userName=$User" `
        -F "password=$Password" `
        -F "database=$Database"
    Write-Host "Extract: $extractResponse"
}

Write-Host ""
Write-Host "Done. $($JsonFiles.Count) file(s) processed."
