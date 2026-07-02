from pathlib import Path

from agorasim.agents import PersonaBank
from agorasim.agents.prompt_builder import load_template, prompt_hash, render
from agorasim.infra import RunManifest


def test_persona_bank_is_deterministic():
    a, b = PersonaBank(50, seed=7), PersonaBank(50, seed=7)
    assert a.content_hash() == b.content_hash()
    assert a.content_hash() != PersonaBank(50, seed=8).content_hash()


def test_prompt_render_fills_all_slots():
    t = load_template("agent_system.j2")
    out = render(t, persona="You are a retail investor: test persona.")
    assert "{{" not in out and "JSON" in out


def test_manifest_roundtrip(tmp_path: Path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("run_id: x\n")
    m = RunManifest.create("x", "P2", cfg, persona_bank_hash="abc",
                           prompt_hashes={"agent_system.j2": prompt_hash("t")},
                           model_ids=["m"], seed=1)
    p = m.write(tmp_path)
    assert p.exists() and "config_sha256" in p.read_text()
