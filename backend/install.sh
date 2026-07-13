#!/usr/bin/env bash
# install.sh — set up the pdf-graph-builder backend for Ollama-based ingest.
# Works on macOS, Linux, and Windows (Git Bash).
# Requires Python 3.11 or 3.12.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------
# 1. Find a suitable Python (prefer 3.12, accept 3.11)
# ------------------------------------------------------------------
find_python() {
    for cmd in python3.12 python3.11 py; do
        if command -v "$cmd" &>/dev/null; then
            ver=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            major=${ver%%.*}
            minor=${ver##*.}
            if [[ "$major" -eq 3 && "$minor" -ge 11 ]]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    # Windows py launcher fallback
    for flag in -3.12 -3.11; do
        if py "$flag" --version &>/dev/null 2>&1; then
            ver=$(py "$flag" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            minor=${ver##*.}
            if [[ "$minor" -ge 11 ]]; then
                echo "py $flag"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python) || {
    echo "ERROR: Python 3.11 or 3.12 is required but was not found."
    echo "Install it from https://www.python.org/downloads/ and re-run this script."
    exit 1
}

echo "Using Python: $PYTHON ($($PYTHON --version 2>&1))"

# ------------------------------------------------------------------
# 2. Create the virtual environment if it doesn't already exist
# ------------------------------------------------------------------
VENV_DIR="$SCRIPT_DIR/venv"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    $PYTHON -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR — reusing it."
fi

# ------------------------------------------------------------------
# 3. Activate
# ------------------------------------------------------------------
if [[ -f "$VENV_DIR/Scripts/activate" ]]; then
    # Windows (Git Bash)
    source "$VENV_DIR/Scripts/activate"
else
    source "$VENV_DIR/bin/activate"
fi

echo "Activated: $(which python) ($(python --version))"

# ------------------------------------------------------------------
# 4. Upgrade pip silently
# ------------------------------------------------------------------
python -m pip install --upgrade pip --quiet

# ------------------------------------------------------------------
# 5. Install dependencies
#    Uses requirements-ollama.txt — the minimal set for Ollama + scaffold-diff ingest.
#    Excludes torch/unstructured/sentence-transformers (not needed when IS_EMBEDDING=False).
# ------------------------------------------------------------------
echo "Installing dependencies from requirements-ollama.txt ..."
pip install -r requirements-ollama.txt

echo ""
echo "Done. To start the backend:"
echo "  source venv/bin/activate   # or venv\\Scripts\\activate on Windows"
echo "  uvicorn score:app --reload"
