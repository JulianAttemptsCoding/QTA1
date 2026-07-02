"""AgoraSim: LLM-agent retail crowd simulation for small-cap prediction (proof of concept).

Novelty lives in the *idea* (a heterogeneous swarm of small open-weight LLM agents,
fed point-in-time public information, whose aggregate simulated order flow is tested
for behavioral fidelity and incremental predictive information on retail-heavy
small-cap stocks). Execution deliberately uses only well-established components:
vLLM offline batching, a standard call auction, Cont (2001) stylized-fact checks,
IC / Diebold-Mariano / Deflated Sharpe evaluation.
"""
__version__ = "0.0.1"
