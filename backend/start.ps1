# start.ps1 — activate the venv and start the backend.
# Run from the backend folder: .\start.ps1

Set-Location $PSScriptRoot
.\venv\Scripts\Activate.ps1
uvicorn score:app --reload
