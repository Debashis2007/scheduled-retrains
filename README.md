# Use Case: Continual / Scheduled Retrains

**YouTube walkthrough:** [Scheduled Retrains — System Design #Shorts](https://youtu.be/YTpfwU_l61s)

**Design doc:** [docs/DESIGN.md](./docs/DESIGN.md) — architecture, patterns, and why.


**Parent system design:** [03 — Distributed Training & Job Orchestration](../03-distributed-training-orchestration.md)  
**Also references:** [08 — Fine-tuning / eval data pipelines](../08-finetuning-eval-data-pipelines.md)

## Users & problem

Production models retrain on a schedule (nightly/weekly) with fresh blessed data. Runs must be reliable, reproducible, and auto-gated before serving canaries.

## Requirements & SLOs

| Requirement | Target |
|-------------|--------|
| Schedule | Cron / event-triggered |
| Reproducibility | Pins for code, data, hardware SKU |
| Gate | Eval pass before registry promote |
| Alerting | Fail the pipeline loudly |

## Design (from parent)

```
Scheduler → resolve blessed dataset@version
  → launch train job (prod priority)
  → checkpoint → offline evals
  → promote artifact to registry (or stop)
  → hand off to serving canary ([05](../05-model-monitoring-observability.md))
```

## Specializations

| Concern | Scheduled retrain choice |
|---------|--------------------------|
| Trigger | Time + data-arrival watermarks |
| Idempotency | One successful run per period |
| Rollback | Keep n previous prod artifacts |
| Cost | Budget cap per run |

## Failure modes

- Partial data day → watermark not closed; skip run.
- Eval flake blocks forever → quarantined flake policy + on-call.
- Train succeeds, canary fails → do not flip alias; page owners.




## Design walkthrough (opens on GitHub)

> **Watch on YouTube:** [Scheduled Retrains — System Design #Shorts](https://youtu.be/YTpfwU_l61s)


![Design overview](docs/video/design-overview.gif)

Full narrated video (download): [docs/video/design-overview.mp4](docs/video/design-overview.mp4)

## Run (self-contained POC)

This folder is a **standalone** project (safe to split into its own GitHub repo).

```bash
cd scheduled-retrains
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. python -m uvicorn app.main:app --reload --port 8000
```

```bash
curl -s http://127.0.0.1:8000/health | jq
```

curl -s -X POST http://127.0.0.1:8000/runs -H 'Content-Type: application/json' -d '{"dataset":"blessed@v2","eval_score":0.91}' | jq

---

**Copyright (c) 2026 Debashis Bhattacharjee. All Rights Reserved.**  
Unauthorized copying or redistribution of this material is prohibited.  
GitHub: [Debashis2007](https://github.com/Debashis2007)

