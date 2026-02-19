#!/usr/bin/env bash
# Wrapper for openai_usage.py and anthropic_usage.py that resolves API keys
# from OpenClaw config when they aren't already in the environment.
#
# Usage: bash run.sh --days 7
#        bash run.sh --days 30 --json
#        bash run.sh --costs-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${HOME}/.openclaw/openclaw.json"

read_config_key() {
  local key_path="$1"
  if [ -f "$CONFIG_FILE" ]; then
    python3 -c "
import json, sys
try:
    with open('$CONFIG_FILE') as f:
        cfg = json.load(f)
    keys = '${key_path}'.split('.')
    val = cfg
    for k in keys:
        val = val.get(k, {})
    print(val if isinstance(val, str) else '')
except Exception:
    print('')
" 2>/dev/null
  fi
}

if [ -z "${OPENAI_ADMIN_KEY:-}" ]; then
  KEY="$(read_config_key "skills.entries.api-usage.apiKey")"
  if [ -n "$KEY" ]; then
    export OPENAI_ADMIN_KEY="$KEY"
  fi
fi

if [ -z "${ANTHROPIC_ADMIN_KEY:-}" ]; then
  KEY="$(read_config_key "skills.entries.api-usage.anthropicKey")"
  if [ -n "$KEY" ]; then
    export ANTHROPIC_ADMIN_KEY="$KEY"
  fi
fi

HAS_OPENAI=false
HAS_ANTHROPIC=false

if [ -n "${OPENAI_ADMIN_KEY:-}" ]; then
  HAS_OPENAI=true
fi
if [ -n "${ANTHROPIC_ADMIN_KEY:-}" ]; then
  HAS_ANTHROPIC=true
fi

if [ "$HAS_OPENAI" = false ] && [ "$HAS_ANTHROPIC" = false ]; then
  echo "Error: No API keys configured." >&2
  echo "Set at least one of:" >&2
  echo "  openclaw config set skills.entries.api-usage.apiKey \"sk-admin-...\"" >&2
  echo "  openclaw config set skills.entries.api-usage.anthropicKey \"sk-ant-admin-...\"" >&2
  exit 1
fi

if [ "$HAS_OPENAI" = true ]; then
  python3 "${SCRIPT_DIR}/openai_usage.py" "$@"
fi

if [ "$HAS_ANTHROPIC" = true ]; then
  if [ "$HAS_OPENAI" = true ]; then
    echo ""
  fi
  python3 "${SCRIPT_DIR}/anthropic_usage.py" "$@"
fi

if [ "$HAS_OPENAI" = false ]; then
  echo "  (OpenAI skipped: no admin key configured)" >&2
fi
if [ "$HAS_ANTHROPIC" = false ]; then
  echo "  (Anthropic skipped: no admin key configured)" >&2
fi
