"""Offline batched inference harness (vLLM). SKELETON: runs on the Vertex worker, not locally.

Design (backup-first, resume-safe):
- Input : JSONL of {request_id, persona_id, model_id, prompt, sampling{temperature, seed}}.
- Output: JSONL of {request_id, raw_text, parsed(bool)}; appended atomically per chunk;
          a request_id ledger makes reruns idempotent (skip already-answered ids).
- Chunks of <= 2048 prompts; ledger + outputs synced to GCS after every chunk, so a
  spot/preemptible kill loses at most one chunk (failure mode F-02 in PLAN.md).

Throughput assumptions are NOT trusted until measured by scripts/p0_gate_throughput.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def answered_ids(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    return {r["request_id"] for r in iter_jsonl(out_path)}


def run_offline(requests_path: Path, out_path: Path, model_id: str,
                max_new_tokens: int = 160, chunk: int = 2048) -> None:  # pragma: no cover
    try:
        from vllm import LLM, SamplingParams  # heavy import; Vertex worker only
    except ImportError as e:
        raise RuntimeError(
            "vLLM not installed. This module runs inside the Vertex custom job image "
            "(see infra/vertex_launch.py). Locally, use tests + smoke scripts only."
        ) from e
    done = answered_ids(out_path)
    todo = [r for r in iter_jsonl(requests_path) if r["request_id"] not in done]
    llm = LLM(model=model_id, dtype="auto", gpu_memory_utilization=0.90)
    with out_path.open("a") as out:
        for i in range(0, len(todo), chunk):
            batch = todo[i:i + chunk]
            params = [SamplingParams(temperature=r["sampling"]["temperature"],
                                     seed=r["sampling"]["seed"],
                                     max_tokens=max_new_tokens) for r in batch]
            results = llm.generate([r["prompt"] for r in batch], params)
            for req, res in zip(batch, results):
                out.write(json.dumps({"request_id": req["request_id"],
                                      "raw_text": res.outputs[0].text}) + "\n")
            out.flush()
