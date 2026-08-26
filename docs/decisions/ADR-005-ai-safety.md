# ADR-005: AI Safety Model — Read-Only by Default

## Status
Accepted

## Context
Cloud Cost Lab includes an AI Cloud Cost Advisor that uses LLMs to analyze costs, explain anomalies, and prioritize recommendations. We must decide what level of autonomy the AI component should have.

## Decision
AI is **read-only by default**. It may analyze, summarize, explain, and recommend — but it must never directly execute destructive actions.

### AI MAY:
- Analyze cost data
- Summarize trends
- Explain anomalies
- Prioritize recommendations
- Answer natural-language questions about costs
- Suggest optimization actions

### AI MUST NOT directly:
- Delete resources
- Modify IAM policies
- Change firewall rules
- Destroy Terraform infrastructure
- Delete databases
- Disable monitoring
- Execute any destructive production change

### Action Workflow
```
AI Analysis
    ↓
Recommendation (with evidence)
    ↓
Human Approval (explicit)
    ↓
Validated Action (logged)
    ↓
Audit Log
```

## Alternatives Considered

### Fully autonomous AI agent
- Pro: Faster optimization, no human bottleneck
- Con: Risk of destructive actions, hard to audit, unpredictable
- Verdict: Unacceptable risk for infrastructure management

### AI with limited write access (e.g., labeling only)
- Pro: Some automation benefit
- Con: Scope creep risk, harder to reason about boundaries
- Verdict: Start read-only, extend carefully in future if needed

### No AI at all
- Pro: Simpler system, no LLM dependency
- Con: Misses learning opportunity, less useful for complex analysis
- Verdict: AI adds value for analysis — just constrain its actions

## Trade-offs
- **Safety over speed** — human approval adds latency but prevents disasters
- **Transparency over autonomy** — all AI reasoning is logged and auditable
- **Pluggable provider** — not locked to one LLM vendor
- **Optional feature** — system works fully without AI enabled

## Consequences
- AI module is a separate optional component
- AI receives structured context (not raw database access)
- All AI responses are logged in audit_logs
- Human approval gate is mandatory for any action
- AI provider is configurable via environment variable
- System is fully functional without AI enabled
- Future: could add Mode 4 (controlled automation) for safe, bounded actions only
