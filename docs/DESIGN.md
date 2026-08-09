# Design: Scheduled Retrains

**Project:** `scheduled-retrains`  
**Parent system design:** `03-distributed-training-orchestration.md / 08`

## 1. What this POC demonstrates

Scheduled train run that only starts on blessed data and promotes on eval gate.

## 2. Architecture (POC)

```text
POST /runs {dataset, eval_score} → promote?
```

## 3. Patterns used (and why)

| Pattern | Why used | Where in code |
|---------|----------|---------------|
| Blessed-only train input | Lineage and poison control. | `blessed@` prefix. |
| Eval gate before alias flip | Bad model must not become prod. | `promoted` flag. |
| Artifact identity | Rollback needs named artifacts. | `artifact` / `alias` fields. |

## 4. Key endpoints

`GET /health`, `POST /runs`

## 5. Tradeoffs / POC limits

No cron scheduler — the HTTP call stands in for the scheduled trigger.

## 6. How to run

See the **Run (self-contained POC)** section in [`../README.md`](../README.md).

This folder is self-contained and can be published as its own GitHub repository.

## 7. Design walkthrough video

> **Watch on YouTube:** [Scheduled Retrains — System Design #Shorts](https://youtu.be/YTpfwU_l61s)
>
> Direct link: **https://youtu.be/YTpfwU_l61s**

Also available in-repo:
- GIF preview: [`video/design-overview.gif`](./video/design-overview.gif)
- MP4 download: [`video/design-overview.mp4`](./video/design-overview.mp4)
- Narration script: [`video/narration.txt`](./video/narration.txt)

