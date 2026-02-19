---
name: research
description: Structure and store research outputs in the brain Obsidian vault. Use when Paro asks for research, comparisons, deep dives, or multi-source summaries that should be saved under `~/dev/brain/research`.
---

# Research Skill

Use this skill whenever Paro asks to "research", "dig into", "compare", or "summarize" topics and we want the results persisted in the brain vault.

## Vault & Paths

- Brain (Obsidian vault) path: `/home/paro/dev/brain`.
- Research root: `/home/paro/dev/brain/research`.

When creating new research outputs:

- Use **kebab-case** for topic folders, e.g. `llm-eval-strategies`, `home-lab-backups`.
- Avoid spaces in folder names.

## Always Use Fresh, Up-to-Date Information

When doing research, prefer **current, authoritative sources** over stale priors.

Tooling rules:

- If `web_search` is available (Brave API key configured), use it for:
  - Discovering recent posts, docs, and comparisons.
  - Getting a quick map of the landscape before diving into specific sources.
- If `web_search` is unavailable or limited:
  - Use the `browser` tool to perform searches via a web UI (e.g. Google, DuckDuckGo) and follow relevant results.
  - Use `web_fetch` on specific URLs to pull readable content.
- Always sanity‑check older knowledge against at least 1–2 fresh sources when the domain is fast‑moving (Kubernetes, LLMs, security, etc.).

When you log the research run, explicitly note whether:

- Web search via API was used (`web_search`),
- Full browser automation was used, and which engines/sites, or
- The answer was based primarily on existing knowledge.

## Standard Layout for a Research Topic

For each topic, create a folder under `research/`:

```text
research/
  <topic>/
    summary.md      # high-level conclusions + recommendations
    sources.md      # links, citations, and key excerpts
    notes-*.md      # optional scratch/working notes
```

### `summary.md`

- Audience: future Paro + Jarvis.
- Keep it concise and opinionated: 1–2 screens max.
- Include:
  - Problem/question statement.
  - Key findings (bulleted).
  - Tradeoffs/risks.
  - Clear recommendations / next steps.

Include a **Related notes** section that uses Obsidian wikilinks when possible, e.g.:

```markdown
## Related notes

- `[[news/dev/<slug>/<tag>_<date>]]` for relevant project-tracker entries.
- `[[research/<other-topic>/summary]]` for adjacent research.
- Any other brain notes that provide useful context.
```

To discover related notes automatically, you may use `obsidian-cli search` / `search-content` in the brain vault (e.g., search by topic keywords, project names, or common tags) and turn high-signal matches into wikilinks.

### `sources.md`

- List all external references (docs, blog posts, issues, etc.).
- For each source, include:
  - URL or location.
  - 1–3 sentence summary.
  - Any critical quote or data point.
- Use Markdown headings or bullets; no need for formal citation formats.

### `notes-*.md`

- Free-form scratch space.
- Name them descriptively, e.g. `notes-initial-pass.md`, `notes-benchmarking.md`.
- It's okay if these are messy; `summary.md` should always be the clean, authoritative view.

## Workflow When Paro Asks for Research

1. **Define the topic folder name**
   - Convert the user’s request to a short, kebab-case slug.
   - Example: "research how to back up my home lab" → `home-lab-backups`.

2. **Create or reuse the topic folder**
   - If `research/<topic>/` exists, append to existing `notes-*.md` and update `summary.md`.
   - Otherwise, create the folder and the initial `summary.md` and `sources.md`.

3. **Do the research (with live web sources)**
   - Use `web_search` when available; fall back to `browser` + `web_fetch` when not.
   - Capture raw findings in a `notes-*.md` file as you go.
   - Prefer primary sources (official docs, RFCs, vendor pages) plus 1–2 good third‑party analyses.

4. **Write/update `summary.md`**
   - Distill the key points and recommendations.
   - Keep the top of the file as the current, authoritative view; if things change, update rather than append random sections.

5. **Populate `sources.md`**
   - Add or update entries for each source actually used.
   - Note which ones look most authoritative or time‑sensitive.

6. **Add related-note wikilinks**
   - Use `obsidian-cli` searches where helpful to find:
     - Project tracker notes, other research topics, or config mirrors that add context.
   - Add these under `## Related notes` in `summary.md`.

7. **Report back in chat**
   - Reply with a concise summary and explicitly mention the path, e.g.:
     - "I’ve saved a detailed write-up in `brain/research/home-lab-backups/summary.md` with sources in `sources.md`."

8. **Log the run**
   - Drop a short log file into `brain/system/logs/` for non-trivial research runs, including:
     - Topic slug.
     - Whether web search or full browser automation was used.
     - Any notable limitations (missing APIs, paywalled sources, etc.).

## When _Not_ to Use This Skill

- Quick, one-off questions where persisting the result has no value.
- Purely local reasoning that doesn’t involve any real "research" or external sources.

In those cases, answer directly without creating a research folder.
