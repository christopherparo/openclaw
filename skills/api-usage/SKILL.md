---
name: api-usage
description: Check OpenAI and Anthropic API usage, costs, and token consumption by model. Supports OpenAI Admin API keys (sk-admin-...) and Anthropic Admin API keys (sk-ant-admin-...).
homepage: https://platform.openai.com/docs/api-reference/usage
metadata: { "openclaw": { "emoji": "📈", "requires": { "bins": ["python3"] } } }
---

# API Usage

Check your OpenAI and Anthropic API usage and costs directly. Supports both providers — configure one or both.

- **OpenAI** — uses the Organization Usage API with an Admin API key (`sk-admin-...`)
- **Anthropic** — uses the Admin API with an Admin API key (`sk-ant-admin-...`)

When both keys are configured, `run.sh` outputs both summaries in sequence. When only one key is present, it runs that provider and prints a note that the other was skipped.

## Quick start

Get a cost summary for the last 7 days:

```bash
bash {baseDir}/scripts/run.sh --days 7
```

Get today's usage with per-model breakdown:

```bash
bash {baseDir}/scripts/run.sh --days 1
```

Get the last 30 days of usage:

```bash
bash {baseDir}/scripts/run.sh --days 30
```

> **Note:** `run.sh` automatically reads keys from your OpenClaw config (`skills.entries.api-usage.apiKey` for OpenAI, `skills.entries.api-usage.anthropicKey` for Anthropic) when the corresponding environment variables are not already set. You can also call each Python script directly if you prefer to export the env vars yourself.

## Output

The script reports (per provider):

1. **Total cost** in USD for the period
2. **Per-model breakdown** — cost and token counts for each model used
3. **Daily breakdown** — cost per day over the period
4. **Category breakdown** — completions, images, audio, embeddings (OpenAI); uncached input, output, cache read, cache write (Anthropic)

## Options

```bash
bash {baseDir}/scripts/run.sh --days 7          # last N days (default: 7)
bash {baseDir}/scripts/run.sh --days 7 --json   # output raw JSON instead of summary
bash {baseDir}/scripts/run.sh --costs-only      # only dollar costs, skip token details
```

## Supported endpoints

**OpenAI** — queries these Organization Usage API endpoints:

- `/v1/organization/costs` — dollar costs grouped by model and day
- `/v1/organization/usage/completions` — token counts for chat/completions
- `/v1/organization/usage/images` — image generation counts
- `/v1/organization/usage/audio_transcriptions` — Whisper transcription usage
- `/v1/organization/usage/embeddings` — embedding token usage

**Anthropic** — queries these Admin API endpoints:

- `/v1/organizations/cost_report` — dollar costs grouped by model/description and day
- `/v1/organizations/usage_report/messages` — token usage (uncached input, output, cache read/write) grouped by model

## Setup

### OpenAI

1. Generate an Admin API key at https://platform.openai.com/settings/organization/admin-keys
2. Add it to your OpenClaw config:

```bash
openclaw config set skills.entries.api-usage.apiKey "sk-admin-YOUR_KEY_HERE"
```

> **Important**: Standard project keys (`sk-proj-...`) will NOT work — they return 403. You need an admin key.

### Anthropic

1. Generate an Admin API key at https://console.anthropic.com/settings/admin-keys
2. Add it to your OpenClaw config:

```bash
openclaw config set skills.entries.api-usage.anthropicKey "sk-ant-admin-YOUR_KEY_HERE"
```

> **Important**: Regular API keys will NOT work — you need an admin key (`sk-ant-admin-...`). Only organization accounts with admin role can create these keys. Individual/personal accounts do not have access to the Admin API.

### Both providers

Or manually edit `~/.openclaw/openclaw.json` and add under `skills.entries`:

```json
"api-usage": {
  "apiKey": "sk-admin-YOUR_OPENAI_KEY_HERE",
  "anthropicKey": "sk-ant-admin-YOUR_ANTHROPIC_KEY_HERE"
}
```

## Anthropic limitations

- The Anthropic cost API only supports daily bucket granularity (`1d`) and a maximum of 31 days per query. Requests for longer periods are automatically clamped.
- Priority Tier costs are not included in the cost endpoint. Track Priority Tier usage via the usage endpoint with the `service_tiers` filter.
- Data freshness is approximately 5 minutes after request completion.
- The Anthropic Admin API requires an **organization account** — individual/personal accounts cannot use it.
