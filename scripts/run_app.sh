#!/usr/bin/env bash
# Princess Mia Application Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo -e "\033[1;35m✨ ✿ Starting Princess Mia Desktop Companion ✿ ✨\033[0m"

# Check if Ollama serve is running
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "\033[1;32m[✓] Ollama model runtime is online on port 11434\033[0m"
else
    echo -e "\033[1;33m[!] Note: Ollama is not detected on port 11434. Fallback heuristics will be used if needed.\033[0m"
fi

python3 pixel_girl.py "$@"
