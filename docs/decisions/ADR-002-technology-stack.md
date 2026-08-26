# ADR-002: Technology Stack

## Status
Accepted

## Context
We need to choose technologies for each layer of Cloud Cost Lab. The choices must balance:
- Learning value (relevant to Cloud/DevOps/SRE career)
- Practical constraints (MacBook M1, 8GB RAM, 256GB SSD)
- Industry relevance
- Simplicity for a single-engineer project

## Decision

| Layer | Technology | Version Target |
|-------|-----------|---------------|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui | Next.js 14+ |
| Backend | FastAPI + Python + Pydantic | Python 3.11+ |
| Database | PostgreSQL | 15+ |
| Cloud | Google Cloud Platform | — |
| IaC | Terraform | 1.5+ |
| CI/CD | GitHub Actions | — |
| Containers | Docker + Docker Compose | — |
| Security | Trivy, Gitleaks | — |

## Alternatives Considered

### Backend: Go + Gin
- Pro: Performance, single binary, strong typing
- Con: Less ecosystem for data analysis, longer development time for prototyping
- Verdict: Python better for data/analytics domain + faster prototyping

### Backend: Node.js + Express
- Pro: Same language as frontend
- Con: Less suitable for data analysis, weaker typing without extra effort
- Verdict: FastAPI provides better API ergonomics (auto-docs, validation)

### Frontend: Vue.js / Svelte
- Pro: Simpler learning curve
- Con: Smaller ecosystem, fewer UI component libraries for dashboards
- Verdict: Next.js has stronger TypeScript support and richer charting ecosystem

### Database: SQLite
- Pro: Zero configuration, no container needed
- Con: No concurrent writes, limited query capabilities
- Verdict: PostgreSQL better represents production patterns

### IaC: Pulumi
- Pro: Real programming languages
- Con: Less industry adoption in GCP ecosystem, smaller community
- Verdict: Terraform is the industry standard for GCP

## Trade-offs
- **Python backend** means two languages in the project (Python + TypeScript), but each is optimal for its domain
- **PostgreSQL** requires a container locally, adding ~100MB RAM usage, but provides realistic production patterns
- **Next.js** is heavier than a simple React SPA, but provides SSR and better routing patterns
- **Terraform** has a learning curve, but is essential for Cloud/DevOps careers

## Consequences
- Docker Compose orchestrates local development (API + DB + Frontend)
- Two package ecosystems to maintain (pip + npm)
- Type safety in both layers (Pydantic + TypeScript)
- All choices are industry-relevant for target career paths
