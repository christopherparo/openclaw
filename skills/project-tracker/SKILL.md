---
name: project-tracker
description: Track OSS projects (GitHub repos) and write release notes into the brain vault on a schedule. Use when Paro wants to "follow" a repo and get summarized release notes under brain/news/dev.
---

# Project Tracker Skill

Use this skill when Paro asks to track an open source project, usually by giving a GitHub URL.

## Concept

Given a GitHub repo (e.g. `https://github.com/argoproj/argo-cd`), the tracker should:

1. **Register the project**
   - Create a config entry under:
     - `/home/paro/dev/brain/system/config/project-tracker/`
   - Config file name: `<owner>-<repo>.json` (e.g. `argoproj-argo-cd.json`).
   - Config fields:
     - `repo`: `owner/repo` (e.g. `argoproj/argo-cd`).
     - `url`: full GitHub URL.
     - `slug`: safe identifier (e.g. `argo-cd`).
     - `lastSeenReleaseTag`: latest release tag that has been processed (or `null` initially).
     - `cronJobId`: ID of the associated OpenClaw cron job (once created).

2. **Create a cron job**
   - Use OpenClaw `cron` tool to add a job that runs **daily** (or at another configured interval) in an **isolated** session.
   - The job’s `agentTurn` message should include:
     - Repo (`owner/repo`).
     - Config path for the project.
     - Target brain path: `/home/paro/dev/brain`.
     - Instructions to:
       - Query the repo’s latest release.
       - Compare against `lastSeenReleaseTag` in the config.
       - If there is a new release, write a new note into the brain under `news/dev/...` (see below).
       - Update `lastSeenReleaseTag` in the config.
       - **Then send a short notification message to the Discord #jarvis channel, mentioning Paro (e.g. `@Flikr`) and pointing to the new release note path in the brain.**

3. **Write release notes into the brain**
   - Base directory for releases:
     - `/home/paro/dev/brain/news/dev/`
   - For repo `owner/repo` (slug `slug`), and a new release with tag `vX.Y.Z` and date `YYYY-MM-DD`, create:
     - `news/dev/<slug>/<tag>_<date>.md`
       - Example: `news/dev/argo-cd/v2.13.0_2025-02-01.md`.

### Release note file structure

Each release note file should:

1. Start with metadata frontmatter:

```markdown
---
Title: <slug> <tag> release (<date>)
Tags:
  - dev-news
  - releases
  - <slug>
  - github
Created: <ISO8601 timestamp>
Repo: <owner/repo>
ReleaseTag: <tag>
ReleaseDate: <date>
Tools:
  - browser (GitHub)
  - web_fetch (GitHub API)
Models:
  - openai-codex/gpt-5.1
---
```

2. Then include:

```markdown
# <slug> <tag> – <human-friendly summary>

## Jarvis summary

- Bullet points of changes that matter to Paro (API or UX changes, breaking changes, infra‑relevant bits, security fixes, etc.).
- Optionally, a short paragraph with overall commentary if appropriate.

## Related notes

- Add Obsidian-style links to other notes that provide context when they exist, for example:
  - `[[research/<topic>/summary]]` for research on the same project.
  - `[[system/config/...]]` for relevant config mirrors.
  - Previous release notes for the same project.

To discover related notes automatically, you may use `obsidian-cli search` / `search-content` in the brain vault (e.g., search for the repo slug or project name) and turn likely matches into wikilinks.

## Release notes

<verbatim or lightly cleaned GitHub release body>

## Links & references

- GitHub release: <https://github.com/<owner>/<repo>/releases/tag/<tag>>
- GitHub repo: <https://github.com/<owner>/<repo>>
- Previous release note (if any): `[[news/dev/<slug>/<prevTag>_<prevDate>]]` or a direct path.
- Any other important docs, blog posts, or migration guides.
```

3. **Optional previous release context**
   - If a previous release note exists for the same repo, load its content and:
     - Call out any notable regressions, reversions, or changes to earlier behavior.
     - Mention these in the `Jarvis summary` section (e.g., “Reverts change introduced in v2.12.0 where …”).

## First-time behavior for a project

- When a project is first registered, **do not backfill** full history.
- Only fetch the **most recent release**:
  - Write a single release note for that latest release.
  - Set `lastSeenReleaseTag` to that tag in the config.

## Implementation Notes

- For GitHub data, prefer the GitHub REST API when available, e.g.:
  - `https://api.github.com/repos/<owner>/<repo>/releases/latest`
  - Or HTML scraping of `/releases/latest` as a fallback.
- Use `web_fetch` to pull release metadata / body from the API or release page.
- Use the `browser` tool when we need to follow links, read attached docs, or interpret complex, rich release pages.
- Use `obsidian-cli` for:
  - Searching for related notes (`search`, `search-content`) to suggest useful wikilinks in the `## Related notes` section.
  - Renaming/moving notes in a link-safe way if we later refactor structure.
- Use the `message` tool from the sub-agent to send Discord notifications when new releases are detected:
  - Channel: `discord`
  - Target: `channel:1472798666799714344`
  - Mention: include `@Flikr` in the message text so Paro sees it.

## When to Use This Skill

- When Paro says things like:
  - "Track this project" (with a GitHub URL).
  - "Keep me up to date on releases for <project>".
- When adding new projects to be tracked.

Once a project is registered, the daily cron job and the project config file handle ongoing tracking; we only need to re-run the skill when adding new repos or changing tracking behavior.
