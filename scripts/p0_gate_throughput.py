"""GATE G0 (compute): thin entrypoint for the Vertex T4 worker image. Delegates to
agorasim.infra.throughput_probe (measures decisions/hour + valid-JSON rate for one model).
NOT runnable locally (needs vLLM + a GPU); the launcher loops it over models. See A-003.
docs/G0_THROUGHPUT.md is assembled locally from the per-model results synced to GCS.
"""
from agorasim.infra.throughput_probe import main

if __name__ == "__main__":
    main()
