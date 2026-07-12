---
name: claude-code-review
description: Cross-model review through Claude Code with local verification. Use when the user requests an independent Claude review or repository policy requires a Claude review pass.
---

# Claude Code Review

Use Claude Code as an independent reviewer, then treat every reported bug as a hypothesis until verified locally. A user request for Claude review authorizes sending the selected repository diff and relevant code context to Anthropic. When repository policy triggers this skill without that explicit request, explain the transmission and obtain confirmation before running Claude.

## 1. Pin the review target

Inspect `git status -sb`, the current branch, and remotes. Use the target supplied by the user: a PR number, base branch, or ref. When omitted, resolve the remote default branch; fall back to `main` or `master` only when that ref exists.

For a branch/ref review, confirm `git diff <target>...HEAD` is non-empty. For a PR review, confirm the PR exists. Stop with a concise explanation when the target cannot be resolved or there is nothing to review.

Completion criterion: one explicit, resolvable target and a non-empty review surface.

## 2. Preflight Claude

Run:

```bash
claude --version
claude auth status
claude ultrareview --help
```

Require a successful login. Inspect only the authentication status; do not repeat identity or credential fields. Ask the user to run `claude auth login` when authentication is missing. Record whether `ultrareview` is available so the next step selects the primary command or fallback.

Completion criterion: Claude is authenticated and one review path is available.

## 3. Run the independent review

Run the review from the repository root:

```bash
claude ultrareview <target> --json --timeout 30
```

Use a PR number for a PR review or the pinned base ref for the current branch. Keep the raw JSON result available for verification. Report timeout, rate-limit, or service failures without retry loops.

If `ultrareview` is unavailable despite a supported Claude CLI, use this read-only fallback:

```bash
claude -p \
  --model opus \
  --effort high \
  --permission-mode plan \
  --no-session-persistence \
  --max-turns 12 \
  "Review git diff <target>...HEAD for correctness bugs, security risks, race conditions, data-loss paths, missing tests, and scope creep. Cite file and line evidence. Return findings only; modify nothing."
```

Completion criterion: a complete Claude result or one explicit external blocker.

## 4. Verify every finding

For each Claude finding:

1. Open the cited file and relevant surrounding code.
2. Confirm the cited behavior exists in the review diff.
3. Trace callers, invariants, and tests needed to establish impact.
4. Run the smallest safe test or static check that can confirm or reject it.
5. Assign one disposition: `confirmed`, `false-positive`, or `unverified` with the missing evidence named.

Do not edit source during review. Apply fixes only when the user separately asks to address confirmed findings.

Completion criterion: every Claude finding has evidence and exactly one disposition.

## 5. Report

Sort confirmed findings by severity and use this shape:

```markdown
## Confirmed

### [P1] Short title — path/to/file.ts:42
Evidence, impact, and the validation that confirmed it.

## Unverified

Findings that need missing runtime, environment, or product evidence.

## Rejected

False positives and the code or test evidence that rejects each one.
```

Omit empty sections. When nothing is confirmed, state that directly and name material review gaps. When Matt's Standards and Spec reviews also ran, keep their axes separate, deduplicate only identical findings, and preserve each review's evidence.
