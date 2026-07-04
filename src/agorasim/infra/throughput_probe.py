"""Vertex T4 job (GATE G0 / A-003): measure decisions/hour + valid-JSON rate for ONE model.

One model per process (process isolation avoids GPU-memory bleed between models); the
launcher loops models in a shell for-loop. Loads the model from the GCS cache written by
model_cache, renders `--n` representative decision prompts via the real templates, runs
them through vLLM generate (raw completion), and parses each output with
agorasim.schemas.parse_decision.

Run: python -m agorasim.infra.throughput_probe --base gs://BUCKET/agorasim --model ID [--n 512]
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time

from agorasim.agents.personas import PersonaBank
from agorasim.agents.prompt_builder import load_template, render
from agorasim.infra.gcs import download_prefix, upload_file
from agorasim.schemas import DECISION_JSON_SCHEMA, parse_decision


def sanitize(model_id: str) -> str:
    return model_id.replace("/", "__")


def build_prompts(n: int) -> list[str]:
    sys_t = load_template("agent_system.j2")
    usr_t = load_template("decision_user.j2")
    # ~30 daily bars + a few headlines => representative ~900-token prompt
    bars = "\n".join(
        f"2024-10-{(d % 28) + 1:02d}, 12.{d % 100:02d}, 12.{(d + 5) % 100:02d}, "
        f"11.{(d + 3) % 100:02d}, 12.{(d + 2) % 100:02d}, {1_000_000 + d * 1234}"
        for d in range(30))
    news = "\n".join(
        f"2024-11-{(d % 14) + 1:02d}T14:00:00Z  Company posts Q update; guidance and product "
        f"headline number {d} with some detail for the reader to weigh."
        for d in range(6))
    bank = PersonaBank(n)
    # Raw text prompts (system + user), NOT chat-template messages. Passing chat messages
    # via llm.chat() puts the instruct model in "assistant" mode where it writes verbose,
    # multi-clause rationales that overflow the 160-token budget and truncate the JSON
    # (valid-JSON ~0.18). Feeding the instruction as a plain completion via llm.generate()
    # yields terse rationales that close within budget -> the operative fix for the valid-
    # JSON gate (G0 >=90%). Guided decoding still enforces the JSON structure either way.
    prompts: list[str] = []
    for i in range(n):
        p = bank.personas[i]
        system = render(sys_t, persona=p.render())
        user = render(usr_t, asof_date="2024-11-15", name_or_alias="ExampleCo (EXMP)",
                      bars_block=bars, news_block=news, shares=p.shares,
                      avg_cost="11.90", cash=f"{p.cash:.0f}")
        prompts.append(f"{system}\n\n{user}")
    return prompts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="gs://BUCKET/agorasim")
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=512)
    args = ap.parse_args()

    from vllm import LLM, SamplingParams  # worker-image only
    from vllm.sampling_params import GuidedDecodingParams

    local = f"/tmp/models/{sanitize(args.model)}"
    nfiles = download_prefix(f"{args.base}/models/{sanitize(args.model)}", local)
    prompts = build_prompts(args.n)
    # Constrain generation to the AgentDecision JSON schema. Without this, small models
    # ramble/loop until max_tokens and emit truncated (invalid) JSON — the operative fix
    # for the >=90% (G0) / >=99% (G2) valid-JSON gates. This is also how the real sim runs.
    # backend="lm-format-enforcer": vLLM's other bundled JSON-schema decoder. Avoids the
    # `outlines` import chain (outlines pulls a broken `pyairports` dep).
    gd = GuidedDecodingParams(json=DECISION_JSON_SCHEMA,
                              backend="lm-format-enforcer")
    # temperature=0.0 (greedy): deterministic, no sampling tail that lengthens rationale.
    sp = SamplingParams(max_tokens=160, temperature=0.0, guided_decoding=gd)

    # max_model_len=4096: the rendered prompt (persona + 30 bars + headlines) plus the
    # 160-token generation must fit; 2048 was tight enough that long personas ate into the
    # generation budget and truncated the JSON. llm.generate (raw completion), not llm.chat.
    llm = LLM(model=local, dtype="half", gpu_memory_utilization=0.90,
              max_model_len=4096, enforce_eager=True)
    t0 = time.time()
    results = llm.generate(prompts, sp)
    dt = time.time() - t0

    texts = [r.outputs[0].text for r in results]
    parsed = [parse_decision(t) for t in texts]
    valid = sum(p is not None for p in parsed) / len(parsed)
    invalid_examples = [t for t, p in zip(texts, parsed) if p is None][:3]
    rec = {"model": args.model, "cache_files": nfiles, "n": len(prompts),
           "secs": round(dt, 2), "decisions_per_hour": round(len(prompts) / dt * 3600),
           "valid_json_rate": round(valid, 4), "guided_decoding": True,
           "invalid_examples": invalid_examples}
    print("THROUGHPUT_RESULT", json.dumps(rec), flush=True)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(rec, tf)
        tmp = tf.name
    upload_file(tmp, f"{args.base}/runs/g0_throughput/{sanitize(args.model)}.json")


if __name__ == "__main__":
    main()
