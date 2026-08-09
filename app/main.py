"""Scheduled Retrains — thin self-contained FastAPI POC."""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from poc_core import MockLLM, TokenBucket, health_payload
from poc_core.safety import SafetyPlane
from poc_core.stores import InMemoryStore, MockVectorIndex

USE_CASE = "Scheduled Retrains"
app = FastAPI(title=USE_CASE)
llm = MockLLM()
store = InMemoryStore()
safety = SafetyPlane()

@app.get("/health")
def health():
    return health_payload(USE_CASE)


import uuid

artifacts: dict[str, dict] = {}

class RunIn(BaseModel):
    dataset: str
    eval_score: float

@app.post("/runs")
def run(body: RunIn):
    if not body.dataset.startswith("blessed@"):
        raise HTTPException(400, detail="dataset not blessed")
    rid = f"run_{uuid.uuid4().hex[:6]}"
    promote = body.eval_score >= 0.85
    artifacts[rid] = {
        "id": rid,
        "dataset": body.dataset,
        "eval_score": body.eval_score,
        "promoted": promote,
        "alias": "prod" if promote else None,
    }
    return artifacts[rid]
