#!/usr/bin/env bash
# Install Graph Builder backend on macOS (Neo4j Desktop + Ollama, no Docker).
# Requires Python 3.12 from Homebrew: brew install python@3.12

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY312="/opt/homebrew/opt/python@3.12/bin/python3.12"

if [[ ! -x "$PY312" ]]; then
  echo "Python 3.12 not found. Install with: brew install python@3.12"
  exit 1
fi

cd "$ROOT/backend"
rm -rf venv
"$PY312" -m venv venv
source venv/bin/activate
pip install --upgrade pip
# Upstream pins torch==2.10.0+cpu which has no wheel on macOS arm64; install standard wheels first.
pip install torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0
grep -v '^torch' requirements.txt | grep -v '^--extra-index-url' > /tmp/requirements-no-torch.txt
pip install -r /tmp/requirements-no-torch.txt
echo "Backend venv ready. Activate with: source backend/venv/bin/activate"
