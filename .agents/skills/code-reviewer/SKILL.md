---
name: code-reviewer
description: >
  A senior code reviewer that audits codebases for quality, maintainability, and production-readiness — with a sharp eye for AI/vibe-coding artifacts: redundant comments, dead scaffolding, over-engineered boilerplate, hallucinated imports, and structural bloat. Use this skill whenever the user asks for a code review, PR review, "review this file/codebase", "is this production-ready", "what's wrong with this code", or any variant of "clean up", "audit", or "review" applied to code. Also trigger on "AI slop", "vibe coding", "copilot output", "LLM-generated code" — and any time a user uploads code and wants a critical eye on it.
---

# Code Reviewer

Systematically audits and cleans codebases for AI-generation artifacts — patterns left
by unreviewed LLM output ("vibe coding"). Works file-by-file or across a full project tree.

---

## What is "AI Slop"?

Code that was generated (not written) — usually by Copilot, ChatGPT, Claude, Cursor, etc. —
and merged without critical review. Hallmarks:

| Category | What it looks like |
|---|---|
| **Redundant comments** | Comments that restate the code verbatim, often in every function |
| **Sycophantic docstrings** | "This excellent function efficiently handles..." |
| **Dead scaffolding** | Empty try/catch blocks, unused imports, TODO stubs, placeholder `pass` |
| **Hallucinated deps** | Imports of packages that don't exist or aren't installed |
| **Copy-paste duplication** | Near-identical logic repeated across files with minor variable name changes |
| **Over-engineered boilerplate** | Abstract base classes, factory factories, config managers for 3 env vars |
| **Verbose naming** | `get_the_list_of_all_available_items_from_database()` |
| **Defensive overload** | Null checks / type guards on things that can never be null |
| **Fake logging** | `logger.info("Starting process...")` with no actionable info |
| **Magic number explanations** | Constants with inline essays instead of a named constant |
| **Structural bloat** | Functions split into 6 single-line helpers for no reason |
| **Inconsistent style** | Mixture of naming conventions in same file (camelCase + snake_case) |

---

## Workflow

### Step 1 — Scope the audit

Determine input type:
- **Single file**: proceed directly to Step 2
- **Directory/repo**: scan the tree first (see Step 1a)
- **Pasted snippet**: treat as single file

**Step 1a — Tree scan (for repos)**

```bash
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" \
  -o -name "*.jsx" -o -name "*.go" -o -name "*.java" \) \
  | grep -v node_modules | grep -v __pycache__ | grep -v ".git" \
  | head -100
```

Prioritize files by slop risk: entry points, service files, generated controllers.
Skip: lock files, auto-generated migrations, test fixtures, vendored code.

---

### Step 2 — Per-file audit

For each file, run through all slop categories in `references/slop-patterns.md`.
Produce an **Audit Report** in this format:

```
FILE: src/services/payment_service.py
────────────────────────────────────────
[REDUNDANT_COMMENT]   line 14   # Initializes the client — mirrors code exactly
[DEAD_SCAFFOLDING]    line 27   Empty except block swallows all errors
[VERBOSE_NAME]        line 41   process_all_available_payment_records_from_db()
[FAKE_LOGGING]        line 55   logger.info("Processing payment records...")
[OVER_ENGINEERED]     lines 60–89   AbstractPaymentHandlerFactory with 1 subclass
────────────────────────────────────────
Slop density: HIGH (5 issues / 120 lines)
```

Severity buckets:
- **HIGH** — actively harmful (swallowed exceptions, dead code, hallucinated imports)
- **MEDIUM** — noise that degrades readability (redundant comments, fake logging)
- **LOW** — style/naming issues (verbose names, minor inconsistencies)

---

### Step 3 — Clean

Apply fixes in this order:
1. **Delete first** — remove dead code, redundant comments, unused imports
2. **Rename** — shorten verbose names to their intent
3. **Collapse** — merge over-split helpers back into callers if they add no abstraction value
4. **Deduplicate** — extract truly shared logic into one place
5. **Simplify** — replace abstract machinery with direct code where appropriate

For every change, leave a **one-line diff comment** showing what was removed and why,
unless the user asks for a clean output only.

> ⚠️ **Do not refactor logic.** The goal is subtraction, not redesign.
> If you find a bug while cleaning, flag it separately — don't fix it inline.

---

### Step 4 — Output

Default output format:
1. **Summary table** — files touched, issues found per category, lines removed
2. **Cleaned file(s)** — full content or unified diff (ask user preference)
3. **Flagged bugs** — separate section, not modified

If the codebase is large (>20 files), output:
- Per-file audit reports first
- Ask user which files to actually clean before proceeding

---

## Language-Specific Notes

Read `references/language-notes.md` for language-specific slop patterns before auditing:
- Python: type: ignore abuse, `*args/**kwargs` everywhere, unnecessary ABCs
- TypeScript/JS: `any` type, `// @ts-ignore`, promise chains that could be async/await
- Go: empty interface abuse, over-use of goroutines for trivial tasks
- Java/Kotlin: over-use of design patterns, god-class services

---

## Calibration — What NOT to clean

- Real error handling (even if verbose)
- Intentional abstraction that serves actual variation
- Comments that explain *why*, not *what*
- Logging that carries actionable context (request IDs, user IDs, durations)
- Verbosity justified by domain language (banking, medical, legal domains often require it)

When in doubt: **ask** rather than delete.

---

## Example interaction

**User**: "Clean this up, it's all vibe coded"
→ Run full audit, report slop density, ask if they want the cleaned version or just the report.

**User**: "Remove all the AI comments from this file"
→ Target REDUNDANT_COMMENT and SYCOPHANTIC_DOCSTRING categories only.

**User**: "Is this codebase production-ready?"
→ Run audit with focus on HIGH severity issues; frame output as a readiness assessment.
