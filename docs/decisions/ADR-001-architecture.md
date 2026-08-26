# ADR-001: Monorepo Architecture

## Status
Accepted

## Context
Cloud Cost Lab needs a frontend (dashboard), backend (API), analytics modules, infrastructure code, and documentation. We need to decide whether to use a monorepo or multiple repositories.

## Decision
Use a single monorepo with clear directory boundaries:
- `apps/api/` — FastAPI backend
- `apps/web/` — Next.js frontend
- `analytics/` — Cost and utilization analysis
- `terraform/` — Infrastructure as Code
- `docs/` — Documentation

## Alternatives Considered

### Multi-repo
- Separate repos for frontend, backend, infra
- Pro: Independent deployment cycles
- Con: Coordination overhead, harder to maintain consistency for a single-engineer project

### Monorepo with Nx/Turborepo
- Pro: Build caching, task orchestration
- Con: Added complexity not justified at this scale

## Trade-offs
- **Simplicity** over deployment independence — single engineer, no team coordination needed
- **Visibility** over isolation — all code in one place for portfolio review
- **Co-located docs** — architecture decisions live next to the code they describe

## Consequences
- All CI/CD runs from one repository
- Docker images built from subdirectories
- Terraform state separate from application code
- Clear boundaries enforced by directory structure, not repository boundaries
