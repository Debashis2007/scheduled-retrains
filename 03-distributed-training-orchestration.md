# 03 — Distributed Training & Job Orchestration

**Prompt:** Design a distributed training / evaluation job platform for frontier models (multi-thousand GPU jobs, preemptible failures, research + product sharing the cluster).

**Rank:** Top 10 (#03)

## Use cases

| Use case | Who | Why this design matters |
|----------|-----|-------------------------|
| Frontier / large pretraining | Research + infra | Gang schedule, topology, checkpoint correctness |
| Post-training (SFT / RLHF / DPO) | Alignment & product teams | Preemptible research vs production queue priority |
| Large offline eval sweeps | Quality / safety | Thousands of short GPU jobs; packing & fairness |
| Shared multi-team GPU cluster | Lab or platform org | Quotas, reservations, cost attribution |
| Continual / scheduled retrains | Production ML | Reliable resume, lineage to data versions |

---

## 1. Clarify requirements

### Functional
- Launch training, fine-tune, and large eval jobs with multi-node GPU topologies.
- Checkpoint / resume; elastic scale where possible.
- Multi-team queues: research experiments vs production post-training.
- Reproducibility: data version, code version, hyperparams, hardware SKU.

### Non-functional
| Concern | Target |
|---------|--------|
| Job start latency | Minutes for large allocs (honest), seconds for small |
| Checkpoint interval | Balanced vs progress loss (e.g. every N minutes / N steps) |
| Failure recovery | Automatic restart from last good checkpoint |
| Utilization | High MFU; minimize idle reserved GPUs |
| Isolation | No cross-job GPU/memory interference; secure data access |

### Scale axes
- GPUs per job, jobs per cluster, data throughput GB/s, checkpoint size TB-class.

### Unacceptable failures
- Silent training divergence from partial node failure
- Checkpoint corruption treated as success
- Retry storms re-poisoning data or blowing storage
- One research job starving production alignment runs

---

## 2. High-level architecture

```
User / CI → Job API → Scheduler (gang + fair share)
                   → Cluster Manager (K8s / custom)
                   → GPU Nodes (NCCL / collective fabric)
                   → Checkpoint Store (object + parallel FS)
                   → Metadata DB (runs, metrics, lineage)
                   → Observability (MFU, loss, stragglers)
```

### Components
1. **Job spec** — image, entrypoint, GPU count, topology constraints, data deps, priority, max runtime.
2. **Gang scheduler** — all-or-nothing placement for SPMD training.
3. **Runtime** — torch/JAX distributed; health checks; watchdog on collectives.
4. **Checkpoint service** — async durable writes; checksums; retention policy.
5. **Data plane** — sharded datasets; streaming readers; cache tiers.
6. **Control plane** — quotas, preemption, drain for maintenance.

---

## 3. Deep dive: failure domains & checkpointing

### Failure types
| Failure | Detection | Response |
|---------|-----------|----------|
| Node death | Heartbeat / NCCL error | Restart job from checkpoint |
| Straggler | Step time skew | Soft alert; replace node if chronic |
| Network brownout | Collective timeouts | Retry with backoff; topology-aware reschedule |
| Silent corruption | Checksum / loss spike | Halt; do not overwrite “latest good” |

### Checkpoint design
- **Frequency tradeoff:** more frequent ⇒ less lost work, more I/O and straggler risk.
- Write to **local NVMe → async drain to object store**; never block forever on remote.
- Keep `latest` and `latest-1`; only advance pointer after checksum + manifest commit.
- For multi-PB checkpoints: sharded writers, parallel upload, bandwidth caps so training doesn’t starve.

**Principal line:** *Checkpoint correctness > clever incremental schemes. A wrong checkpoint wastes more GPUs than conservative I/O.*

---

## 4. Scheduling & multi-tenancy

### Policies
- **Fair share** across orgs/teams with **priority boost** for production post-training.
- **Preemption:** research low-priority jobs checkpoint and yield to prod.
- **Reservations:** capacity calendar for major pretraining runs.
- **Bin packing:** pack small evals onto fragments; keep large contiguous blocks for training.

### Topology awareness
- Prefer jobs within same rail / spine to maximize NCCL bandwidth.
- Don’t place all-reduce heavy jobs across weak cross-region links.

---

## 5. Data pipeline hazards

- Retries that **re-read corrupted shards** can poison gradients → validate shards (checksum, schema) at ingest and at epoch boundaries.
- Exactly-once is hard; aim for **at-least-once + deterministic sample IDs** so duplicates don’t bias silently—or use epoch-level reshuffle seeds recorded in metadata.
- Separate **staging** vs **training-blessed** datasets; only blessed datasets mount into prod jobs.

---

## 6. Observability for training

- **MFU / TFLOP/s utilization**
- Loss curves, grad norm, tokens/s
- Collective wait time vs compute time
- Checkpoint duration and failure rate
- Cost per run (GPU-hours) attributed to team

Alert on: sudden MFU drop (straggler/network), NaN loss, checkpoint SLA breach.

---

## 7. Scale 10× / 100× / 1000×

| Scale | Breakage | Mitigation |
|-------|----------|------------|
| 10× GPUs/job | Collective latency, stragglers | Better topology; ZeRO/FSDP; pipeline stages |
| 100× jobs | Scheduler thrash | Hierarchical queues; reservation windows |
| 1000× cluster | Power, cooling, supply; control plane | Multi-cluster federation; cell architecture |

---

## 8. Security & safety

- Dataset ACLs; no world-readable training data with sensitive corpora.
- Secrets via identity (not baked into images).
- Eval jobs that execute model-generated code → sandboxed runners (tie to agent containment design).
- Audit: who launched what with which data version.

---

## 9. Multi-year bet

**Bet:** Build a **cell-based GPU fabric** with gang scheduling, first-class checkpoint identity, and strict separation of research vs production queues—rather than one giant Kubernetes queue with hope. Invest early in **training observability (MFU, collective health)** as a product, not a dashboard afterthought.

**Why:** Frontier training ROI is dominated by utilization and failed-run recovery, not peak theoretical FLOPs.

---

## 10. 60-second summary

Gang-schedule topology-aware GPU jobs, checkpoint asynchronously with checksummed manifests, preempt research for production, and treat data versioning + corruption detection as part of the training system—not an external ETL concern.
