# scripts/

Operational helper scripts for Cloud Cost Lab.

**Status: empty for now.** Scripts are added only when a phase needs them, for example:

- `seed_demo_data.*` — load the mock dataset into PostgreSQL (Phase 1);
- `run_checks.*` — local validation entry point (lint + tests) (Phase 1+);
- report generation helpers (Phase 15).

## Ground rules

- Scripts are idempotent or clearly state their side effects.
- No secrets in scripts; configuration comes from environment variables.
- Anything that could create/modify GCP resources requires an explicit confirmation flag and is documented in `docs/cost-safety.md` first.
