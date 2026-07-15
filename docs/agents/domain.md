# Domain docs

This repository uses a single domain context.

## Before exploring

Read these files when they exist:

- `CONTEXT.md` at the repository root
- Relevant ADRs under `docs/adr/`

If they do not exist, proceed silently. Domain-modeling skills create them lazily when terminology or architectural decisions need recording.

## Layout

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
└── skills/
```

## Vocabulary

Use terms exactly as defined in `CONTEXT.md` when naming skills, interfaces, issues, tests, or architectural concepts.

If a required concept is missing or conflicts with existing terminology, surface the gap for domain modeling.

## Architectural decisions

Read relevant ADRs before proposing structural changes.

If a proposal contradicts an ADR, identify the conflict explicitly instead of silently overriding it.
