# 05 — Model Monitoring & Behavior Observability

**Prompt:** Design a monitoring system for model behavior at scale—quality, safety, drift, and ops health across chat and API.

**Rank:** Top 10 (#05)

## Use cases

| Use case | Who | Why this design matters |
|----------|-----|-------------------------|
| Canary a new model revision | Serving / release eng | Slice-aware gates before full traffic |
| Catch safety or quality regressions | Trust & product | Behavioral metrics, not only GPU health |
| Cost / token anomaly detection | FinOps + platform | Spend spikes from abuse or bad loops |
| Enterprise SLA reporting | B2B customers | Latency, availability, error budgets by tenant |
| Incident response for “model feels worse” | On-call | Trace version → metrics → sampled sessions |

---

## 1. Clarify requirements

### What “model monitoring” means here
Not only GPU metrics—**behavioral** observability: refusals, toxicity, hallucinations (proxy), latency, cost, and eval regressions tied to model versions.

### Functional
- Real-time metrics + dashboards + alerts.
- Offline eval suites gated on deploy.
- Online sampling for human/LLM-as-judge review.
- Incident workflow: detect → slice → rollback / mitigate.
- Privacy-preserving storage of prompts/responses.

### Non-functional
| Concern | Target |
|---------|--------|
| Metric delay | Seconds for infra; minutes for behavioral aggregates |
| Sampling | Tunable; higher for canaries & risky slices |
| Retention | Hot 7–30d; cold longer for compliance |
| Overhead | ≪ 1–2% of serving cost |

### Unacceptable failures
- Blind deploy (no canary metrics)
- Alert storms that train humans to ignore
- Storing sensitive prompts without controls
- “Green” dashboards while safety regressions ship

---

## 2. Signal taxonomy

| Layer | Examples |
|-------|----------|
| **Infra** | GPU util, TTFT, ITL, error rate, queue depth |
| **Product** | Sessions, retries, regenerates, thumbs down |
| **Safety** | Block rate, category histogram, jailbreak hits |
| **Quality proxies** | Refusal appropriateness, citation presence, tool error rate |
| **Cost** | Tokens in/out per model/version/tenant |

Principal framing: separate **serving health** from **model health**—both required to ship.

---

## 3. High-level architecture

```
Serving path → Telemetry agent (metrics + sampled traces)
            → Stream (Kafka) → Realtime aggregators → Alerts
                            → Feature store / lake → Batch evals
Offline eval runners → Results DB → Launch gate
Human/LLM review UI ← Sampled queues (stratified)
Model registry ← version, canary %, owner, rollback pointer
```

---

## 4. Deep dive: canary + automatic rollback

### Canary design
1. Deploy model `v_new` at 1% traffic (sticky by user hash).
2. Compare vs control `v_old` on shared slices (same traffic shape).
3. Gates (examples):
   - TTFT P99 regression < 10%
   - 5xx < threshold
   - Safety block-rate within band (↑ or ↓ both suspicious)
   - Thumbs-down / regenerate rate
4. Auto-promote or auto-rollback; humans for ambiguous quality.

### Slice-aware monitoring
Aggregate overall averages hide harm. Always slice by:
- Language, country, product surface
- Prompt length / context length bucket
- Topic classifiers (medical, political, child-safety adjacent)
- API vs consumer

> “A 0.1% absolute rise in a high-severity safety category on one slice can be a ship-blocker even if global averages look fine.”

---

## 5. Online evaluation without drowning

- **Stratified sampling:** overweight rare/high-risk classes.
- **LLM-as-judge** for scalable rubrics; calibrate against human panels weekly.
- **Shadow evals:** replay logged prompts on candidate model offline before canary.
- Rate-limit judges; they are another inference fleet with cost/latency.

### Hallucination / quality
- For RAG: citation coverage + groundedness scores.
- For tools: schema validity, execution success.
- For chat: pairwise preference models on sampled sessions.

---

## 6. Privacy, retention, access

- Default: store hashes + metadata; raw text in restricted store with ACL + purpose binding.
- Redact secrets/PII on ingest where possible.
- Employee access: break-glass + audit.
- Regional residency for enterprise tenants.

---

## 7. Alerting philosophy

| Bad | Good |
|-----|------|
| 200 noisy gauges | Few SLO burn alerts + safety page-worthy events |
| Only global averages | Slice-aware anomalies |
| Page on every blip | Multi-window burn rates (error budgets) |

Page for: safety severity spikes, canary gate fail, regional total outage. Ticket for gradual quality drift.

---

## 8. Scale 10× / 100× / 1000×

| Scale | Breakage | Fix |
|-------|----------|-----|
| 10× QPS | Cardinality explosion | Bound labels; pre-aggregate |
| 100× models/experiments | Dashboard sprawl | Model registry as source of truth; standard templates |
| 1000× tenants | Per-tenant noise | Hierarchical: global → tier → tenant opt-in |

---

## 9. Multi-year bet

**Bet:** A **unified model registry + canary contract** where every serving revision must export a standard metrics schema and pass the same gate pipeline. Treat behavioral observability as part of the inference platform API, not a side project per team.

**Why:** At principal scale, the failure mode is organizational—dozens of models shipping with inconsistent telemetry.

---

## 10. 60-second summary

Instrument infra and behavior, canary with slice-aware gates, sample for human/LLM review under privacy controls, and bind every model version to a registry that can roll back automatically when safety or SLO burn warrants it.
