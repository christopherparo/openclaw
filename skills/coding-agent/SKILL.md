---
name: coding-agent
description: "Delegate coding tasks to Codex, Claude Code, or Pi agents via background process. Use when: (1) building/creating new features or apps, (2) reviewing PRs (spawn in temp dir), (3) refactoring large codebases, (4) iterative coding that needs file exploration. NOT for: simple one-liner fixes (just edit), reading code (use read tool), or any work in ~/clawd workspace (never spawn agents here). Requires a bash tool that supports pty:true."
metadata:
  {
    "openclaw": { "emoji": "🧩", "requires": { "anyBins": ["claude", "codex", "opencode", "pi"] } },
  }
---

# Coding Agent (bash-first)

Use **bash** (with optional background mode) for all coding agent work. Simple and effective.

## ⚠️ PTY Mode Required!

Coding agents (Codex, Claude Code, Pi) are **interactive terminal applications** that need a pseudo-terminal (PTY) to work correctly. Without PTY, you'll get broken output, missing colors, or the agent may hang.

**Always use `pty:true`** when running coding agents:

```bash
# ✅ Correct - with PTY
bash pty:true command:"codex exec 'Your prompt'"

# ❌ Wrong - no PTY, agent may break
bash command:"codex exec 'Your prompt'"
```

### Bash Tool Parameters

| Parameter    | Type    | Description                                                                 |
| ------------ | ------- | --------------------------------------------------------------------------- |
| `command`    | string  | The shell command to run                                                    |
| `pty`        | boolean | **Use for coding agents!** Allocates a pseudo-terminal for interactive CLIs |
| `workdir`    | string  | Working directory (agent sees only this folder's context)                   |
| `background` | boolean | Run in background, returns sessionId for monitoring                         |
| `timeout`    | number  | Timeout in seconds (kills process on expiry)                                |
| `elevated`   | boolean | Run on host instead of sandbox (if allowed)                                 |

### Process Tool Actions (for background sessions)

| Action      | Description                                          |
| ----------- | ---------------------------------------------------- |
| `list`      | List all running/recent sessions                     |
| `poll`      | Check if session is still running                    |
| `log`       | Get session output (with optional offset/limit)      |
| `write`     | Send raw data to stdin                               |
| `submit`    | Send data + newline (like typing and pressing Enter) |
| `send-keys` | Send key tokens or hex bytes                         |
| `paste`     | Paste text (with optional bracketed mode)            |
| `kill`      | Terminate the session                                |

---

## Quick Start: One-Shot Tasks

For quick prompts/chats, create a temp git repo and run:

```bash
# Quick chat (Codex needs a git repo!)
SCRATCH=$(mktemp -d) && cd $SCRATCH && git init && codex exec "Your prompt here"

# Or in a real project - with PTY!
bash pty:true workdir:~/Projects/myproject command:"codex exec 'Add error handling to the API calls'"
```

**Why git init?** Codex refuses to run outside a trusted git directory. Creating a temp repo solves this for scratch work.

---

## The Pattern: workdir + background + pty

For longer tasks, use background mode with PTY:

```bash
# Start agent in target directory (with PTY!)
bash pty:true workdir:~/project background:true command:"codex exec --full-auto 'Build a snake game'"
# Returns sessionId for tracking

# Monitor progress
process action:log sessionId:XXX

# Check if done
process action:poll sessionId:XXX

# Send input (if agent asks a question)
process action:write sessionId:XXX data:"y"

# Submit with Enter (like typing "yes" and pressing Enter)
process action:submit sessionId:XXX data:"yes"

# Kill if needed
process action:kill sessionId:XXX
```

**Why workdir matters:** Agent wakes up in a focused directory, doesn't wander off reading unrelated files (like your soul.md 😅).

---

## Reliable completion detection for coding agents

When Jarvis (or any orchestrator) spawns a coding agent in the background, the hardest
part is knowing **when it finished** and **whether it succeeded**. Coding agents do not
have a standard "I'm done" signal — their stdout is noisy, and they may or may not honor
prompt-based completion hooks.

The solution is `coding-agent-wrap.sh` (bundled with this skill). It wraps any coding
agent command, captures its exit code, and emits a **deterministic, grep-able marker** at
the very end of stdout. Jarvis should **always** start coding agents through this wrapper
when running them in the background.

### How to launch a wrapped coding agent

Use `bash` with `pty:true` and `background:true`. Pass the wrapper script with a `--label`
to identify the run, then `--` followed by the actual agent command:

```bash
bash pty:true workdir:~/project background:true command:"coding-agent-wrap.sh --label test-run -- opencode run 'Run the test suite and fix failures'"
# → returns sessionId: XXX
```

This starts the coding agent in a background PTY session. The wrapper runs the agent,
waits for it to exit, then prints the completion marker.

### Marker format

The wrapper always emits one of these lines as the last meaningful output:

```
[CODING_AGENT_DONE label=test-run status=success exit_code=0]
[CODING_AGENT_DONE label=test-run status=error exit_code=1]
```

### How Jarvis should detect completion

After launching the wrapped agent in background, Jarvis should follow this two-step flow:

1. **Poll until the session exits.** Use `process action:poll` with a generous timeout to
   check when the background session finishes. When `details.status` is `"completed"` or
   `"failed"`, the process has exited.

2. **Read the log and find the marker.** Use `process action:log` to fetch the session
   output, then look for the `[CODING_AGENT_DONE` line. Extract the `status` and
   `exit_code` fields from it.

```
# Step 1: Poll until done
process action:poll sessionId:XXX timeout:30000
# → when details.status == "completed" or "failed", move to step 2

# Step 2: Read the log and extract the marker
process action:log sessionId:XXX
# → search output for: [CODING_AGENT_DONE label=test-run status=success exit_code=0]
# → the marker is always the last meaningful line
```

**Detection rules:**

| Signal                                        | Meaning                                                         |
| --------------------------------------------- | --------------------------------------------------------------- |
| `details.status == "completed"` or `"failed"` | Process exited — safe to read the log                           |
| Output contains `[CODING_AGENT_DONE`          | Wrapper ran to completion — parse `status=` and `exit_code=`    |
| No marker found but process exited            | Wrapper was killed or crashed — fall back to `details.exitCode` |

### Quick start examples

```bash
# One-shot (foreground) with completion marker
bash pty:true workdir:~/project command:"coding-agent-wrap.sh --label fix-auth -- opencode run 'Fix the auth bug'"

# Background with completion marker
bash pty:true workdir:~/project background:true command:"coding-agent-wrap.sh --label build-api -- codex exec --full-auto 'Build a REST API'"
# → sessionId: XXX — poll and read log as described above
```

### Wrapper flags

| Flag            | Description                                                                                                           |
| --------------- | --------------------------------------------------------------------------------------------------------------------- |
| `--label LABEL` | Identifies this run in the marker (default: `"default"`)                                                              |
| `--notify`      | Also fires `openclaw system event` on completion (if `openclaw` CLI is available) — see "Optional: auto-notify" below |
| `--`            | Separator between wrapper flags and the agent command                                                                 |

---

## Codex CLI

**Model:** `gpt-5.2-codex` is the default (set in ~/.codex/config.toml)

### Flags

| Flag            | Effect                                             |
| --------------- | -------------------------------------------------- |
| `exec "prompt"` | One-shot execution, exits when done                |
| `--full-auto`   | Sandboxed but auto-approves in workspace           |
| `--yolo`        | NO sandbox, NO approvals (fastest, most dangerous) |

### Building/Creating

```bash
# Quick one-shot (auto-approves) - remember PTY!
bash pty:true workdir:~/project command:"codex exec --full-auto 'Build a dark mode toggle'"

# Background for longer work
bash pty:true workdir:~/project background:true command:"codex --yolo 'Refactor the auth module'"
```

### Reviewing PRs

**⚠️ CRITICAL: Never review PRs in OpenClaw's own project folder!**
Clone to temp folder or use git worktree.

```bash
# Clone to temp for safe review
REVIEW_DIR=$(mktemp -d)
git clone https://github.com/user/repo.git $REVIEW_DIR
cd $REVIEW_DIR && gh pr checkout 130
bash pty:true workdir:$REVIEW_DIR command:"codex review --base origin/main"
# Clean up after: trash $REVIEW_DIR

# Or use git worktree (keeps main intact)
git worktree add /tmp/pr-130-review pr-130-branch
bash pty:true workdir:/tmp/pr-130-review command:"codex review --base main"
```

### Batch PR Reviews (parallel army!)

```bash
# Fetch all PR refs first
git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'

# Deploy the army - one Codex per PR (all with PTY!)
bash pty:true workdir:~/project background:true command:"codex exec 'Review PR #86. git diff origin/main...origin/pr/86'"
bash pty:true workdir:~/project background:true command:"codex exec 'Review PR #87. git diff origin/main...origin/pr/87'"

# Monitor all
process action:list

# Post results to GitHub
gh pr comment <PR#> --body "<review content>"
```

---

## Claude Code

```bash
# With PTY for proper terminal output
bash pty:true workdir:~/project command:"claude 'Your task'"

# Background
bash pty:true workdir:~/project background:true command:"claude 'Your task'"
```

---

## OpenCode

```bash
bash pty:true workdir:~/project command:"opencode run 'Your task'"
```

---

## Pi Coding Agent

```bash
# Install: npm install -g @mariozechner/pi-coding-agent
bash pty:true workdir:~/project command:"pi 'Your task'"

# Non-interactive mode (PTY still recommended)
bash pty:true command:"pi -p 'Summarize src/'"

# Different provider/model
bash pty:true command:"pi --provider openai --model gpt-4o-mini -p 'Your task'"
```

**Note:** Pi now has Anthropic prompt caching enabled (PR #584, merged Jan 2026)!

---

## Parallel Issue Fixing with git worktrees

For fixing multiple issues in parallel, use git worktrees:

```bash
# 1. Create worktrees for each issue
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

# 2. Launch Codex in each (background + PTY!)
bash pty:true workdir:/tmp/issue-78 background:true command:"pnpm install && codex --yolo 'Fix issue #78: <description>. Commit and push.'"
bash pty:true workdir:/tmp/issue-99 background:true command:"pnpm install && codex --yolo 'Fix issue #99 from the approved ticket summary. Implement only the in-scope edits and commit after review.'"

# 3. Monitor progress
process action:list
process action:log sessionId:XXX

# 4. Create PRs after fixes
cd /tmp/issue-78 && git push -u origin fix/issue-78
gh pr create --repo user/repo --head fix/issue-78 --title "fix: ..." --body "..."

# 5. Cleanup
git worktree remove /tmp/issue-78
git worktree remove /tmp/issue-99
```

---

## ⚠️ Rules

1. **Always use pty:true** - coding agents need a terminal!
2. **Respect tool choice** - if user asks for Codex, use Codex.
   - Orchestrator mode: do NOT hand-code patches yourself.
   - If an agent fails/hangs, respawn it or ask the user for direction, but don't silently take over.
3. **Be patient** - don't kill sessions because they're "slow"
4. **Monitor with process:log** - check progress without interfering
5. **--full-auto for building** - auto-approves changes
6. **vanilla for reviewing** - no special flags needed
7. **Parallel is OK** - run many Codex processes at once for batch work
8. **NEVER start Codex in ~/clawd/** - it'll read your soul docs and get weird ideas about the org chart!
9. **NEVER checkout branches in ~/Projects/openclaw/** - that's the LIVE OpenClaw instance!

---

## Progress Updates (Critical)

When you spawn coding agents in the background, keep the user in the loop.

- Send 1 short message when you start (what's running + where).
- Then only update again when something changes:
  - a milestone completes (build finished, tests passed)
  - the agent asks a question / needs input
  - you hit an error or need user action
  - the agent finishes (include what changed + where)
- If you kill a session, immediately say you killed it and why.

This prevents the user from seeing only "Agent failed before reply" and having no idea what happened.

---

## Optional: Auto-Notify on Completion

> The primary way to detect completion is the **poll + log** flow described in
> "Reliable completion detection for coding agents" above. The notification mechanisms
> below are **optional extras** — they provide an immediate wake signal but are not
> required for correct detection.

### Wrapper --notify flag (reliable)

Pass `--notify` to the wrapper. After the agent exits, it fires `openclaw system event`
in addition to the completion marker:

```bash
bash pty:true workdir:~/project background:true command:"coding-agent-wrap.sh --label todos-api --notify -- codex --yolo exec 'Build a REST API for todos.'"
```

The wrapper emits `[CODING_AGENT_DONE label=todos-api status=success exit_code=0]` AND
fires an `openclaw system event` — you get both a grep-able marker and an immediate wake.

### Prompt-based notification (best-effort)

If you cannot use the wrapper, append a wake trigger to your prompt. This relies on the
coding agent choosing to run the command, so it is less reliable:

```
... your task here.

When completely finished, run this command to notify me:
openclaw system event --text "Done: [brief summary of what was built]" --mode now
```

**Example:**

```bash
bash pty:true workdir:~/project background:true command:"codex --yolo exec 'Build a REST API for todos.

When completely finished, run: openclaw system event --text \"Done: Built todos REST API with CRUD endpoints\" --mode now'"
```

This triggers an immediate wake event — but only if the agent actually runs the command.

---

## Learnings (Jan 2026)

- **PTY is essential:** Coding agents are interactive terminal apps. Without `pty:true`, output breaks or agent hangs.
- **Git repo required:** Codex won't run outside a git directory. Use `mktemp -d && git init` for scratch work.
- **exec is your friend:** `codex exec "prompt"` runs and exits cleanly - perfect for one-shots.
- **submit vs write:** Use `submit` to send input + Enter, `write` for raw data without newline.
- **Sass works:** Codex responds well to playful prompts. Asked it to write a haiku about being second fiddle to a space lobster, got: _"Second chair, I code / Space lobster sets the tempo / Keys glow, I follow"_ 🦞
