"""GATE G2 smoke: end-to-end tiny run with NO GPU and NO network.
Uses a stub 'model' (rule-based text generator emitting plausible JSON + occasional
garbage) to exercise: personas -> prompts -> parse -> imbalance + auction -> manifest.
PASS if >= 99% parse-valid and outputs + manifest written under runs/smoke-local/.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from agorasim.agents import PersonaBank
from agorasim.agents.prompt_builder import load_template, prompt_hash, render
from agorasim.infra import RunManifest
from agorasim.market import call_auction, flow_imbalance
from agorasim.schemas import parse_decision

OUT = Path("runs/smoke-local")


def stub_llm(persona_render: str, rng: random.Random) -> str:
    if rng.random() < 0.005:
        return "lol just buy the dip"          # exercises the failure path
    action = rng.choices(["buy", "sell", "hold"], weights=[4, 3, 3])[0]
    qty = 0 if action == "hold" else rng.choice([5, 10, 25, 100])
    payload = {"action": action, "qty": qty,
               "confidence": round(rng.uniform(0.2, 0.9), 2), "rationale": "smoke"}
    if action != "hold" and rng.random() < 0.6:   # limit orders so the auction price can move
        drift = rng.uniform(-0.03, 0.05) if action == "buy" else rng.uniform(-0.05, 0.03)
        payload |= {"order_type": "limit", "limit_price": round(10.0 * (1 + drift), 2)}
    return json.dumps(payload)


def main() -> None:
    rng = random.Random(0)
    bank = PersonaBank(20, seed=1337)
    sys_t = load_template("agent_system.j2")
    OUT.mkdir(parents=True, exist_ok=True)
    price, rows, n_valid, n_total = 10.0, [], 0, 0
    for day in range(10):
        decisions = []
        for p in bank.personas:
            prompt = render(sys_t, persona=p.render())
            raw = stub_llm(prompt, rng)
            n_total += 1
            d = parse_decision(raw)
            if d:
                n_valid += 1
                decisions.append(d)
        ib = flow_imbalance(decisions)
        auc = call_auction(decisions, last_price=price)
        price = auc.price if auc.volume else price
        rows.append({"day": day, "imbalance": ib, "price": price, "volume": auc.volume})
    (OUT / "sim.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    m = RunManifest.create("smoke-local", "P2", Path("configs/sim_smoke.yaml"),
                           persona_bank_hash=bank.content_hash(),
                           prompt_hashes={"agent_system.j2": prompt_hash(sys_t)},
                           model_ids=["stub"], seed=0)
    m.write(OUT)
    frac = n_valid / n_total
    print(f"parse-valid: {frac:.3f}  days: 10  final_price: {price:.2f}")
    assert frac >= 0.99, "GATE G2 FAIL: parse-valid below 0.99"
    print("GATE G2 SMOKE: PASS")


if __name__ == "__main__":
    main()
