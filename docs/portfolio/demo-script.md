# Demo Script — Cloud Cost Lab (5 Minutes)

## Setup

```bash
# Start API (demo mode, no GCP needed)
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --port 8000

# Start frontend
cd apps/web && npm run dev
```

---

## 1. Overview Dashboard (1 min)

Open: http://localhost:3000

**Show:**
- Current month cost ($X)
- Previous month cost
- Month-over-month change (+X%)
- Projected cost for full month
- Potential savings available

**Say:** "This is the overview. I can see at a glance that costs increased X% this month, the projection is $X, and there's $X in potential savings we haven't captured yet."

---

## 2. Cost Explorer (30 sec)

Navigate: `/cost`

**Show:**
- Daily cost trend chart (30-day area chart)
- Cost breakdown by service (Compute Engine dominates)
- Cost by project (production highest)
- Cost by environment (production > staging > dev)

**Say:** "The cost explorer shows where money goes. Compute Engine is 65% of spend, production is 70%. The trend shows a spike on the 15th — that's an anomaly we'll investigate."

---

## 3. Resource Inventory (1 min)

Navigate: `/resources`

**Show:**
- Table with 8 resources, utilization bars
- Note the idle-test-server: CPU 3%, owner UNALLOCATED
- Click into a resource detail: cost chart + CPU chart + metadata + labels

**Say:** "Every resource is tracked with cost and utilization. This idle server has 3% CPU for 30 days — clearly waste. Note the UNALLOCATED owner — our governance policy flags this as a violation."

---

## 4. Recommendations (1 min)

Navigate: `/recommendations`

**Show:**
- Total potential savings summary
- Top recommendation: "Idle compute resource detected"
- Evidence: "CPU averaged 3.0% over 30 days"
- Priority score, risk level, confidence
- Approval required indicator

**Say:** "The recommendation engine found $X/month in savings. Each recommendation shows evidence, not just a guess. This idle VM could save $21/month by scheduling — low risk, high confidence. But it requires human approval before any action."

---

## 5. AI Advisor (30 sec)

Call API:
```bash
curl -X POST http://localhost:8000/api/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Where can I save the most money?"}'
```

**Show the response:**
- Summary: "Found $X/month in potential savings..."
- Evidence with specific resources
- Risk and confidence assessment
- Safety note: "AI is read-only"

**Say:** "The AI advisor answers natural language questions. It's read-only — can analyze and recommend, but cannot delete or modify anything. Every response includes evidence and a safety note."

---

## 6. Savings & Lifecycle (30 sec)

Call API:
```bash
curl http://localhost:8000/api/savings
```

**Show:**
- Potential: X recommendations, $X/month
- Approved: 1 item, awaiting implementation
- Implemented: 1 item, awaiting verification
- Verified (REALIZED): 1 item, actual savings confirmed
- Rejected: 1 item, with reason

**Say:** "We distinguish potential from realized savings. Only after we implement AND verify with actual billing data do we call it 'realized.' This prevents claiming savings we haven't actually achieved."

---

## 7. Wrap-Up (30 sec)

**Show:** API docs at http://localhost:8000/docs

**Say:** "Everything runs in demo mode without GCP credentials. When connected to real billing data, the same engine works on actual costs. The system has 329 tests, CI/CD with security scanning, Terraform for infrastructure, and SRE practices with incident response procedures. It's designed to be the kind of tool I'd want as a Cloud Engineer."

---

## Key Messages

1. **Evidence-based**: every recommendation shows observed data
2. **Safe**: human approval required, AI is read-only
3. **Complete**: cost → utilization → recommendation → savings verification
4. **Production-quality**: tests, CI/CD, observability, incident response
5. **GCP-native**: BigQuery, Monitoring, IAM, Terraform
