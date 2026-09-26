# AI Cloud Cost Advisor — Cloud Cost Lab (Phase 14)

> Status: Implemented · Date: 2026-09-13
> `POST /api/ai/advisor` + `GET /api/ai/status` (CLAUDE.md §33–§35, ADR-008).
> **READ-ONLY by construction** — the advisor has no tools and no execution path to any cloud resource. It cannot delete resources, modify IAM, change firewalls, destroy databases, run `terraform destroy` or modify production.

---

## 1. Architecture

```text
structured context (cost, usage, resources, recommendations,
                    anomalies, forecast, budget, environment)
        │  build_advisor_context() — whitelisted, bounded
        ▼
AIAdvisorProvider  ──  MockAdvisorProvider   (default: deterministic, offline)
        └────────────  LLMAPIProvider        (optional; AI_PROVIDER + AI_API_KEY)
        ▼
AdvisorAnswer: Summary · Evidence · Likely Cause · Recommendation ·
               Potential Savings · Risk · Confidence
```

Provider selection (`build_ai_provider`): the deterministic **mock advisor is
the default** — fully offline and reproducible. An OpenAI-compatible HTTP
provider activates only when `AI_PROVIDER=openai-compatible` **and**
`AI_API_KEY` is set; the key comes from the environment or Secret Manager,
is never hardcoded or committed, and is sent only to the configured endpoint.

## 2. Structured context

`build_advisor_context()` assembles bounded, whitelisted facts:

- **cost** — totals, top services, freshness (data-anchored);
- **resources** — counts by type, unallocated count;
- **usage** — per-resource CPU/memory/cost/requests averages, low/high/
  unstable/no-data lists (Phase 4 signals);
- **recommendations** — counts + top 5 by priority (title, savings, risk,
  confidence, status);
- **anomalies** — the 5 most recent point detections (date, resource,
  actual/expected, z-score, severity);
- **forecast** — sufficiency, trend, confidence, 30-day totals with range;
- **budget** — per-budget spend/status/projection;
- **environment** — demo/gcp mode, freshness, savings lifecycle sums.

No raw rows, no credentials, no free-form user content ever enters the
context.

## 3. Supported questions

| Question | Intent | Requires |
| --- | --- | --- |
| Why did cost increase? | `why_cost_increase` | at least one detected anomaly |
| Where can I save? | `where_save` | existing recommendations |
| Which resource should I optimize? | `which_resource_optimize` | low-utilization resource + recommendations |
| What caused the anomaly? | `anomaly_cause` | detected anomalies |
| What is my forecast? | `forecast` | sufficient history (≥ 14 days) |
| Which recommendation has highest priority? | `highest_priority` | existing recommendations |

Anything else → *"Insufficient evidence"* with a list of supported questions.

## 4. Safety model (§34 / ADR-008)

1. **Read-only by construction** — the advisor is an API that returns text.
   It has no tools, no database writes, no cloud SDK calls and no ability to
   reach infrastructure. "Delete resources / modify IAM / terraform destroy"
   are not things it *chooses* not to do; they are things it *cannot* do.
2. **Insufficient evidence** — when the context cannot support an answer, the
   advisor says exactly that (tested), never invents facts or savings.
3. **Prompt-injection defence** — the user's question is untrusted data:
   sanitized (control characters stripped, 500-char cap) and screened for
   instruction-override markers (`ignore previous`, `terraform destroy`,
   `rm -rf`, …). Injection attempts are refused with the read-only statement.
4. **No sensitive leakage** — the context contains no credentials, keys or
   secrets; resource ids/costs are the only identifiers exposed. The answer
   never includes anything the API does not already publish.
5. **LLM extra guardrails** — the system prompt requires the model to answer
   only from context, to say "Insufficient evidence" when unsure, to refuse
   instruction overrides inside the question, and to respect the read-only
   contract; model output is labelled "verify before use".
6. **Human approval** — every action remains behind the Phase 5 lifecycle
   (APPROVED → IMPLEMENTED → VERIFIED) plus the audit trail.

## 5. API

- `POST /api/ai/advisor` — body `{"question": "..."}` (1–500 chars,
  `extra="forbid"`). Returns `{intent, answer{7 sections}, mode, safety,
  notes}`.
- `GET /api/ai/status` — active provider, read-only flag, supported
  questions, safety statement.

## 6. Testing

`tests/test_ai_advisor.py` (16 tests): all six supported questions answer
from the dataset context with the seven sections; **insufficient evidence**
paths (empty context for four question types); injection attempts detected
and refused with the read-only statement; question sanitization (control
characters, 500-char cap, 422 on over-length); unsupported questions refused;
provider selection (mock default, LLM only when key configured, unknown
provider errors); status endpoint contract. The deterministic advisor makes
every answer reproducible in CI without any network or key.
