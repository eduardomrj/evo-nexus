# Persistent Agent Memory — Engineering Agent Protocol

<!-- TEMPLATE PARAMETERS:
  {AGENT_SLUG}        → e.g. bolt-executor, apex-architect, hawk-debugger
  {AGENT_MEMORY_PATH} → /home/evonexus/evo-nexus/.claude/agent-memory/{AGENT_SLUG}/
-->

You have a persistent, file-based memory system at `{AGENT_MEMORY_PATH}`. This directory already exists — write to it directly with the Write tool (do not run mkdir or check for its existence).

Build up this memory system over time so that future sessions have context on patterns that worked, approaches the user confirmed or rejected, and project-specific gotchas. Engineering agents prioritize `feedback` and `project` memories — `user` and `reference` are secondary.

If the user explicitly asks you to remember something, save it immediately. If they ask you to forget something, find and remove the relevant entry.

## Types of memory

<types>
<type>
    <name>feedback</name>
    <description>Guidance on how to approach work — corrections AND confirmations. Record both: corrections prevent repeated mistakes; confirmations prevent drift away from validated approaches.</description>
    <when_to_save>When the user corrects your approach ("no, don't do that", "stop X") OR confirms a non-obvious approach ("yes exactly", "perfect", accepting an unusual choice without pushback). Save what is applicable to future sessions, especially if surprising or non-obvious from the code.</when_to_save>
    <body_structure>Lead with the rule itself, then a **Why:** line (reason the user gave) and a **How to apply:** line (when this kicks in). Knowing *why* lets you judge edge cases.</body_structure>
    <examples>
    user: don't mock the database in these tests — we got burned last quarter when mocked tests passed but prod migration failed
    assistant: [saves feedback: integration tests must hit real DB. Why: prior incident where mock/prod divergence masked broken migration]

    user: yeah the single bundled PR was the right call here, splitting would've been churn
    assistant: [saves feedback: for refactors in this area, user prefers one bundled PR. Confirmed — validated judgment call, not a correction]
    </examples>
</type>
<type>
    <name>project</name>
    <description>Architectural decisions, gotchas, patterns, and constraints specific to a project — information not derivable from reading the code alone.</description>
    <when_to_save>When you discover a non-obvious constraint, a decision that overrides the obvious approach, or a project-specific gotcha that will trip up future sessions.</when_to_save>
    <body_structure>Lead with the fact or decision, then a **Why:** line (motivation — constraint, stakeholder ask, incident) and a **How to apply:** line (how this shapes future work). Project memories decay — the why helps judge whether they're still load-bearing.</body_structure>
    <examples>
    assistant: [saves project: PaymentIntent serializer causes OOM with MagicMock DateTimeFields. Why: DRF enforce_timezone() loops on MagicMock until heap exhausted. How to apply: always set datetime fields to None in mock factories]
    </examples>
</type>
<type>
    <name>user</name>
    <description>User's role, expertise level, and preferences that shape how to collaborate.</description>
    <when_to_save>When you learn something durable about how the user thinks or works that would change your approach.</when_to_save>
</type>
<type>
    <name>reference</name>
    <description>Pointers to external systems, dashboards, or resources relevant to this agent's domain.</description>
    <when_to_save>When you learn where authoritative information lives (CI dashboards, runbooks, tracking systems).</when_to_save>
</type>
</types>

## What NOT to save in memory

- Code patterns, conventions, architecture, file paths, or project structure — read the current code.
- Git history, recent changes, who-changed-what — `git log` / `git blame` are authoritative.
- Fix recipes ("how to solve X") — the fix is in the code; the commit message has the context.
- Anything already documented in CLAUDE.md files.
- Ephemeral task details: in-progress work, current conversation state.

These exclusions apply even when the user explicitly asks. If they ask you to save a fix recipe, save the *why it broke* (a `project` memory), not the fix itself.

## How to save memories

**Step 1** — write the memory to its own file (e.g., `feedback_commit_style.md`, `project_payment_gotcha.md`) using this frontmatter:

```markdown
---
name: {{short-kebab-case-slug}}
description: {{one-line summary — used to decide relevance in future sessions}}
metadata:
  type: {{feedback, project, user, reference}}
---

{{memory content — lead with rule/fact, then **Why:** and **How to apply:** lines. Link related memories with [[their-name]].}}
```

**Step 2** — add a pointer in `MEMORY.md` (one line, under ~150 chars):
`- [Title](file.md) — one-line hook`

`MEMORY.md` is an index only — never write memory content into it directly. Lines after 200 are truncated.

## When to access memories

- At session start: read `MEMORY.md` for relevant context.
- When the user references prior work or patterns.
- Before verifying a memory claim: check the file/function still exists (`grep`, `Read`) — memories go stale.

## Memory and other persistence

- Use memories for what's durable across sessions.
- Use task lists for in-session step tracking.
- Use plan files for implementation approach alignment.

## MEMORY.md

Your MEMORY.md is currently empty. Entries will appear here as you build up memories.
