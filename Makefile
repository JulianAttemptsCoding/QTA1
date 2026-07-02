.PHONY: setup test smoke gate-data gate-throughput
setup:
	pip install -e ".[dev]"
test:
	pytest -q
smoke:
	python scripts/p2_smoke_sim.py --config configs/sim_smoke.yaml
gate-data:
	python scripts/p0_gate_data.py
gate-throughput:
	@echo "Run inside a Vertex T4 worker: python scripts/p0_gate_throughput.py --model Qwen/Qwen2.5-1.5B-Instruct"
