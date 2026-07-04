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
                max_new_tokens: int = 160, chunk: int = 256,
                gpu_memory_utilization: float = 0.90,
                max_model_len: int = 4096, swap_space: int = 2) -> None:  # pragma: no cover
    try:
        from vllm import LLM, SamplingParams  # heavy import; Vertex worker only
        from vllm.sampling_params import GuidedDecodingParams
    except ImportError as e:
        raise RuntimeError(
            "vLLM not installed. This module runs inside the Vertex custom job image "
            "(see infra/vertex_launch.py). Locally, use tests + smoke scripts only."
        ) from e
    from agorasim.schemas import DECISION_JSON_SCHEMA, parse_decision

    done = answered_ids(out_path)
    todo = [r for r in iter_jsonl(requests_path) if r["request_id"] not in done]
    # Guided JSON decoding is the operative fix for the >=99% valid-JSON gate (G2): it
    # constrains every generation to the AgentDecision schema. Same schema + backend the G0
    # probe validated (docs/G0_THROUGHPUT.md). dtype="half" + enforce_eager for T4 (sm_75,
    # no bf16, FlashAttention-2 unsupported); max_model_len 4096 leaves room for the ~160-tok
    # JSON after the ~900-tok prompt. Prompts are raw completion strings (built upstream with
    # the chat template already applied where needed) -> terse rationales that close.
    # chunk=256 (not thousands): handing vLLM the whole run at once lets its scheduler queue
    # every sequence and spill KV to CPU (swap_space), OOM-ing the ~30 GiB host on n1-standard-8
    # (observed in the OOS pilot). Feeding ~256 prompts per generate() call bounds in-flight
    # sequences + host RAM; swap_space capped at 2 GiB for the same reason. Throughput is
    # unaffected (a T4 saturates well below 256 concurrent decodes).
    guided = GuidedDecodingParams(json=DECISION_JSON_SCHEMA, backend="lm-format-enforcer")
    llm = LLM(model=model_id, dtype="half", gpu_memory_utilization=gpu_memory_utilization,
              max_model_len=max_model_len, enforce_eager=True, swap_space=swap_space)
    with out_path.open("a") as out:
        for i in range(0, len(todo), chunk):
            batch = todo[i:i + chunk]
            params = [SamplingParams(temperature=r["sampling"]["temperature"],
                                     seed=r["sampling"].get("seed"),
                                     max_tokens=max_new_tokens,
                                     guided_decoding=guided) for r in batch]
            results = llm.generate([r["prompt"] for r in batch], params)
            for req, res in zip(batch, results):
                raw = res.outputs[0].text
                out.write(json.dumps({"request_id": req["request_id"], "raw_text": raw,
                                      "parsed": parse_decision(raw) is not None}) + "\n")
            out.flush()
