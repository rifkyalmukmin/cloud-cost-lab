# AI Cloud Cost Advisor — Cloud Cost Lab

## Overview

The AI Cloud Cost Advisor analyzes cloud cost data and provides structured, evidence-based responses to natural language questions. It is **READ-ONLY by default** — it can analyze, summarize, explain, and recommend, but cannot execute any destructive actions.

## Safety Model

### AI MAY:
- Analyze cost data and trends
- Summarize spending patterns
- Explain cost increases and anomalies
- Prioritize optimization recommendations
- Answer natural-language questions about costs
- Suggest actions for humans to take

### AI MUST NOT:
- Delete resources
- Modify IAM policies
- Change firewall rules
- Destroy Terraform infrastructure
- Delete databases
- Disable monitoring
- Execute any write operation on infrastructure

### Safety Enforcement

Every response includes:
```json
"safety_note": "AI is read-only and cannot perform destructive actions"
```

Destructive questions are blocked:
```json
{
  "summary": "Cannot process this request",
  "evidence": "AI cannot perform destructive actions. Detected: 'delete'"
}
```

## API Endpoints

### POST /api/ai/ask

Ask the advisor a question.

**Request:**
```json
{
  "question": "Why did cost increase this month?"
}
```

**Response:**
```json
{
  "summary": "Cost increased 15.2% compared to previous month",
  "evidence": "Month-over-month change: 15.2%; Top service: Compute Engine ($245.30, 65.2%); Anomaly detected on 2026-08-15: +262% (Compute Engine)",
  "likely_cause": "Cost spike detected — Compute Engine on vm-prod-api-01",
  "recommendation": "Review top-spending services and investigate anomalies.",
  "potential_savings": 42.50,
  "risk": "LOW",
  "confidence": "HIGH",
  "safety_note": "AI is read-only and cannot perform destructive actions"
}
```

### GET /api/ai/capabilities

List what the AI can and cannot do.

## Supported Questions

| Question Type | Keywords Detected |
|---------------|-------------------|
| Cost increase analysis | "increase", "rose", "spike", "why did cost" |
| Savings opportunities | "save", "reduce", "optimize", "cut cost" |
| Idle resources | "idle", "unused", "which resource" |
| Anomaly investigation | "anomaly", "unexpected", "spike" |
| Cost forecast | "forecast", "predict", "future", "next month" |
| Priority ranking | "priority", "first", "most important", "highest" |
| Budget status | "budget", "spend", "limit" |

## Context Data

The AI receives structured context from all application services:

```
cost: current month, previous month, MoM change, projected
cost_by_service: service breakdown with percentages
cost_by_project: project breakdown with percentages
utilization: resource utilization with patterns
recommendations: top optimization opportunities (max 10)
forecast: monthly expected + range
anomalies: detected anomalies (max 5)
budget: limit, current spend, utilization %, status
```

All sensitive data is filtered before context injection (no keys, credentials, or tokens).

## Safety Protections

### 1. Input Sanitization
- Control characters stripped
- Input length capped (1000 chars)
- Forbidden action keywords detected and blocked

### 2. Sensitive Data Filtering
Fields matching these patterns are removed from context:
- service_account_key
- private_key
- secret
- password
- credential
- token
- api_key
- billing_account_id

### 3. Prompt Injection Protection
- Questions are sanitized before processing
- No raw user input reaches backend services
- Context is pre-built from structured data (not from user input)

### 4. Insufficient Evidence Handling
When data is insufficient, the AI explicitly states:
```json
{
  "summary": "Insufficient evidence",
  "evidence": "Not enough historical data to generate a reliable forecast",
  "confidence": "LOW"
}
```

## Architecture

```
User Question
    ↓
  Input Sanitization (safety.py)
    ↓
  Question Validation (no destructive actions)
    ↓
  Context Building (context.py)
    ↓
  Sensitive Data Filtering
    ↓
  Analysis Engine (advisor.py)
    ↓
  Structured Response
    ↓
  Safety Note Appended
```

## Pluggable LLM Support

The current implementation uses a rule-based analysis engine (no external API needed). For enhanced natural language capabilities:

1. Set `AI_PROVIDER` environment variable
2. Set `AI_API_KEY`
3. The structured context is formatted as a prompt for the LLM
4. LLM responses are validated against safety rules before returning

The system works fully without an LLM provider — the rule-based engine handles all supported question types.

## Testing

24 tests covering:
- Input sanitization (control chars, length limits)
- Question validation (destructive actions blocked)
- Sensitive data filtering (nested structures)
- All question types (7 categories + general)
- Destructive question rejection
- Safety note inclusion in every response
- Insufficient evidence handling
- API endpoints (ask, capabilities)
