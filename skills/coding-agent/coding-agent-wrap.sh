#!/usr/bin/env bash
# coding-agent-wrap.sh — Wrapper for coding agents (opencode, claude, codex, pi)
# that captures exit code and emits a structured completion marker.
#
# Usage:
#   coding-agent-wrap.sh [--label LABEL] [--notify] -- <command...>
#
# Options:
#   --label LABEL   Optional label to identify this run (default: "default")
#   --notify        Also fire 'openclaw system event' on completion (if openclaw is available)
#   --              Separator; everything after this is the command to run
#
# Output markers (always written to stdout at the very end):
#   [CODING_AGENT_DONE label=<label> status=success exit_code=0]
#   [CODING_AGENT_DONE label=<label> status=error exit_code=<N>]
#   [CODING_AGENT_DONE label=<label> status=signal signal=<SIG>]
#
# These markers are designed for Jarvis/OpenClaw to detect in process:log or
# process:poll output without ambiguity.

set -euo pipefail

LABEL="default"
NOTIFY=false

# Parse wrapper flags (everything before --)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label)
      LABEL="$2"
      shift 2
      ;;
    --notify)
      NOTIFY=true
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      # No -- separator; treat remaining args as the command
      break
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "Error: no command specified." >&2
  echo "Usage: coding-agent-wrap.sh [--label LABEL] [--notify] -- <command...>" >&2
  exit 1
fi

# Run the coding agent command, capturing its exit code
EXIT_CODE=0
"$@" || EXIT_CODE=$?

# Determine status
if [[ $EXIT_CODE -eq 0 ]]; then
  STATUS="success"
  MARKER="[CODING_AGENT_DONE label=${LABEL} status=success exit_code=0]"
else
  STATUS="error"
  MARKER="[CODING_AGENT_DONE label=${LABEL} status=error exit_code=${EXIT_CODE}]"
fi

# Emit the structured marker (always, to stdout)
echo ""
echo "$MARKER"

# Optionally fire an openclaw system event for immediate wake
if [[ "$NOTIFY" == "true" ]]; then
  if command -v openclaw &>/dev/null; then
    openclaw system event --text "Coding agent finished (${LABEL}): ${STATUS}, exit code ${EXIT_CODE}" --mode now 2>/dev/null || true
  fi
fi

exit $EXIT_CODE
