"""GATE G0 (compute): run INSIDE a Vertex T4 worker. Measures real decisions/hour:
- load each configs/models.yaml model under vLLM,
- run 512 representative prompts (persona + 30 bars + 5 headlines, ~900 tok in / 120 out),
- record tokens/s and valid-JSON rate via agorasim.schemas.parse_decision,
- write docs/G0_THROUGHPUT.md and refresh the FEASIBILITY.md cost table.
Budget lines in FEASIBILITY.md are estimates until this gate replaces them with measurements.
"""
