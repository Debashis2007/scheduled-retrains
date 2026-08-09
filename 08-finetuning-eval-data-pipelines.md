# 08 — Fine-Tuning / Eval Data Pipelines

**Prompt:** Design high-throughput data pipelines for fine-tuning and evaluation that survive corrupted inputs, guarantee lineage, and avoid poisoning training runs.

**Rank:** Top 10 (#08)

## Use cases

| Use case | Who | Why this design matters |
|----------|-----|-------------------------|
| Domain fine-tuning | Vertical products (legal, medical, code) | Blessed datasets + lineage to checkpoints |
| Preference / RLHF data prep | Alignment teams | Rater guidelines versioning; quality gates |
| Continuous eval suites | Quality / release | Eval firewall against train leakage |
| Synthetic data generation | Scale limited human data | Teacher version pins; mix ratios; collapse checks |
| Prod-log learning (policy-permitted) | Platform ML | PII controls, quarantine, poison resistance |

---

## 1. Clarify requirements

### Functional
- Ingest diverse sources: human feedback, prod samples (policy-permitted), synthetic data, vendor datasets, eval suites.
- Validate, dedupe, filter, annotate, version, and publish “blessed” datasets.
- Feed training jobs and continuous eval harnesses.
- Support schema evolution (JSONL / columnar / multimodal).

### Non-functional
| Concern | Example |
|---------|---------|
| Throughput | GB/s–TB/day class for large orgs |
| Poison resistance | Corrupt or adversarial batches don’t silently train |
| Lineage | Any trained checkpoint → exact data versions |
| Latency to publish | Hours for prod FT; faster for experimental |
| Privacy | PII controls; residency; retention |

### Unacceptable failures
- Training on unblessed / rejected data
- Eval contamination (train/test leakage)
- Undetected schema drift crashing jobs mid-run
- Retry amplification doubling toxic content weight

---

## 2. High-level architecture

```
Sources → Ingest Landing (immutable raw)
       → Validation & Quarantine
       → Transform / Filter / Annotate
       → Dedupe & Dedup-eval vs held-out
       → Blessed Registry (dataset@version)
       → Feature / packing for trainers
       → Train & Eval consumers
       → Metrics & poison detectors back into filters
```

**Immutable raw + versioned blessed** is the spine.

---

## 3. Deep dive: validation at GB/s

### Layered checks
1. **Structural:** JSON schema, required fields, utf-8, max size.
2. **Statistical:** length histograms, label balance, language ID.
3. **Safety/PII:** classifiers; quarantine hits.
4. **Checksum:** per-shard merkle; manifest of shard digests.
5. **Canary poison tests:** inject known probes; ensure filters catch.

### Quarantine workflow
- Failed shards → quarantine bucket + reason codes.
- Do not block entire corpus for one bad shard unless critical.
- Human/ops review queues for systematic failures.

### Throughput tactics
- Parallel shard workers; columnar formats (Parquet) where possible.
- Incremental validation on append-only landing.
- Backpressure to connectors when quarantine rate spikes.

> “At 5GB/s, if 0.1% is corrupt and you ‘skip with warning,’ you may still poison a lot of tokens. Prefer quarantine + rate-based circuit breakers.”

---

## 4. Lineage & reproducibility

Dataset manifest includes:
- `dataset_id`, `semver` or content-addressed hash
- Source snapshots / commit IDs
- Filter code version + params
- Embedding / teacher model versions for synthetic data
- Train job records pointer to manifest

Training job must refuse to start without resolvable blessed manifest.

---

## 5. Dedup & leakage

- Exact hash dedup + fuzzy near-dup (MinHash/SimHash) within train.
- **Eval firewall:** block any train example above similarity threshold to eval sets.
- Separate teams/permissions for eval ground truth when needed.

Leakage is a silent quality lie—treat as Sev-ish for flagship evals.

---

## 6. Human feedback & synthetic data

| Stream | Risks | Controls |
|--------|-------|----------|
| Prod logs | Privacy, bias, consent | Policy gates; anonymization; opt-in enterprise |
| Rater data | Instruction drift | Rater guidelines versioning; gold checks |
| Synthetic | Model collapse / echo | Mix ratios; diversity metrics; teacher version pin |

---

## 7. Packing for trainers

- Shuffle buffers with recorded seeds.
- Sequence packing for efficiency; document packing rules in manifest.
- Deterministic resume: sample IDs so restarts don’t skew epochs silently.

---

## 8. Scale 10× / 100× / 1000×

| Scale | Breakage | Fix |
|-------|----------|-----|
| 10× ingest | Validator CPU | Scale workers; push down checks to native code |
| 100× datasets | Registry sprawl | Namespaces; GC policy; content-addressed storage |
| 1000× multimodal | Storage & scan cost | Tiered scan intensity; sample-based heavy checks |

---

## 9. Multi-year bet

**Bet:** Make **content-addressed blessed datasets** the only legal input to production training, with automated eval-leakage gates in CI. Invest in poison/anomaly detection as continuous production systems, not one-off scripts.

---

## 10. 60-second summary

Land raw data immutably, validate and quarantine at shard granularity, publish only versioned blessed manifests, firewall eval leakage, and bind every training run to lineage—so retries and corrupt JSONL can’t silently buy you a bad model.
