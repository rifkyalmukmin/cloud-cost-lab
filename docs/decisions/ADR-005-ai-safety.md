# ADR-005 — AI Advisor is Read-Only by Default

> Status: Accepted · Date: 2026-09-05 · Phase: 0 (advisor itself is Phase 16)

## Context

An AI-assisted cost analysis layer is an explicit project goal ("AI Cloud Cost Advisor"): answering questions like *"Where can I save the most money?"* or *"Why did cost increase this week?"*. LLMs are good at exactly this kind of summarization and explanation — and notoriously unsafe when given write access to infrastructure. Additional constraints:

- The system must stay auditable and trustworthy (its whole point is evidence-based recommendations).
- The author's laptop cannot host a local LLM; external providers introduce token cost and data-sharing considerations.
- The project's credibility depends on not making claims the data does not support.

## Decision

- The AI layer is **READ-ONLY by default**: it may analyze, summarize, explain, prioritize, and recommend — nothing else.
- The AI provider is **pluggable** behind an interface (no vendor lock-in); `AI_PROVIDER=none` disables the feature entirely.
- The model receives **structured, bounded context** (pre-aggregated metrics, top-N lists, budget status, anomalies — never raw credentials or raw full-table dumps).
- AI output follows a fixed shape: **Summary · Evidence · Likely Cause · Recommendation · Potential Savings · Risk · Confidence**.
- AI recommendations enter the **same lifecycle as rule-based ones**: `OPEN → APPROVED → IMPLEMENTED → VERIFIED` with human approval before any action, and every AI interaction is written to the audit log.
- Explicitly forbidden for the AI: deleting/modifying production resources, changing IAM or firewall rules, destroying Terraform infrastructure, deleting databases, disabling monitoring.

The safety workflow:

```text
AI analysis → Recommendation → Human approval → Validated action → Audit log
```

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Agentic AI with tool access (can "fix" issues directly) | One hallucinated action can delete infrastructure; the audit story collapses; unacceptable for a cost-safety-focused project |
| No AI at all | Loses a named project goal and a real skill dimension (AI-assisted engineering); the read-only pattern is itself the safe, employable design |
| Locally hosted LLM | Not feasible on 8 GB RAM; external pluggable provider chosen instead |

## Trade-offs

- **Less demo spectacle:** the AI cannot "just fix it" on stage. Accepted — the approval workflow *is* the demo.
- **Hallucination risk remains** even read-only: mitigated by feeding structured evidence, demanding confidence levels, and labelling AI output as analysis, not fact.
- **Token cost & data exposure:** bounded context windows; no credentials in prompts; provider choice keeps the option of privacy-conscious endpoints.

## Consequences

- Positive: AI adds value (explanation, prioritization, root-cause narratives) without expanding the blast radius; the trust model stays coherent — every impactful change, human- or AI-suggested, passes the same human gate and audit log.
- Negative: some "wow factor" is consciously traded for safety; the advisor's usefulness depends heavily on context quality, which becomes a Phase 16 engineering task.
- Rule added: if automation modes are ever introduced (observation → recommendation → approval → controlled automation), the AI layer caps at **recommendation mode**; controlled automation remains a separately approved, bounded, human-configured feature.
