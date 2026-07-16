# Repository instructions

## Agent skills

### Issue tracker

Issues are tracked in Linear under team `thattimc`, project `skills`. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the default `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix` labels. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository using root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

## Repository structure

- `skills/` contains published, independently installable skills only.
- Keep published skill directories flat at `skills/<skill-name>/`.
- Every skill contains `SKILL.md` and `agents/openai.yaml`.
- The `SKILL.md` frontmatter `name` matches the skill directory name.
- User-only skills pair `disable-model-invocation: true` with `policy.allow_implicit_invocation: false` in `agents/openai.yaml`.
- Every published skill has exactly one canonical link in `README.md`.
- Keep `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` versions synchronized.
- Keep skill-owned scripts, references, assets, and templates inside their owning skill directory.
- Do not add drafts, personal skills, or deprecated skills under `skills/`.

Before completing structural changes, run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/check_structure.py
```
