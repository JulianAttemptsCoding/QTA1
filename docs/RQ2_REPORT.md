# RQ2 Calibration Fidelity Report

- Source: P3 Vertex calibration `sim.jsonl` artifacts.
- Target: daily simulated flow imbalance vs Robintrack daily holder-count change.

| Scope | Ticker | Arm | N | Spearman | Sign agree | Mean entropy |
| --- | --- | --- | --- | --- | --- | --- |
| ticker | BLNK | alias | 127 | 0.160 | 0.535 | 1.085 |
| ticker | BLNK | named | 127 | 0.153 | 0.535 | 1.076 |
| ticker | CRBP | alias | 127 | 0.154 | 0.693 | 1.072 |
| ticker | CRBP | named | 127 | 0.137 | 0.693 | 1.060 |
| ticker | GOLD | alias | 127 | -0.131 | 0.535 | 0.929 |
| ticker | GOLD | named | 127 | -0.156 | 0.535 | 0.960 |
| ticker | IGC | alias | 127 | 0.187 | 0.543 | 1.069 |
| ticker | IGC | named | 127 | 0.092 | 0.535 | 1.068 |
| ticker | IIPR | alias | 127 | 0.036 | 0.354 | 1.054 |
| ticker | IIPR | named | 127 | 0.073 | 0.354 | 1.048 |
| ticker | LEVI | alias | 127 | 0.111 | 0.354 | 1.073 |
| ticker | LEVI | named | 127 | 0.157 | 0.354 | 1.084 |
| ticker | PLUG | alias | 127 | 0.050 | 0.638 | 0.995 |
| ticker | PLUG | named | 127 | -0.020 | 0.638 | 0.975 |
| ticker | RIOT | alias | 127 | 0.033 | 0.417 | 1.026 |
| ticker | RIOT | named | 127 | 0.037 | 0.417 | 1.017 |
| ticker | VKTX | alias | 127 | 0.119 | 0.827 | 1.069 |
| ticker | VKTX | named | 127 | 0.142 | 0.827 | 1.073 |
| ticker | XXII | alias | 127 | -0.103 | 0.346 | 1.037 |
| ticker | XXII | named | 127 | -0.059 | 0.346 | 1.048 |
| pooled | ALL | alias | 1270 | 0.044 | 0.524 | 1.041 |
| pooled | ALL | named | 1270 | 0.036 | 0.524 | 1.041 |

## Named vs Alias

- Named-vs-alias sign-agreement gap: `-0.001`.
- Named-vs-alias Spearman gap: `-0.008`.

## Gate G3

- G3 kill condition does not fire on the available P3 artifacts.

## Figures

- `docs/figures/p3/p3_event_BLNK_alias.svg`
- `docs/figures/p3/p3_event_BLNK_named.svg`
- `docs/figures/p3/p3_event_CRBP_alias.svg`
- `docs/figures/p3/p3_event_CRBP_named.svg`
- `docs/figures/p3/p3_event_GOLD_alias.svg`
- `docs/figures/p3/p3_event_GOLD_named.svg`
- `docs/figures/p3/p3_event_IGC_alias.svg`
- `docs/figures/p3/p3_event_IGC_named.svg`
- `docs/figures/p3/p3_event_IIPR_alias.svg`
- `docs/figures/p3/p3_event_IIPR_named.svg`
- `docs/figures/p3/p3_event_LEVI_alias.svg`
- `docs/figures/p3/p3_event_LEVI_named.svg`
- `docs/figures/p3/p3_event_PLUG_alias.svg`
- `docs/figures/p3/p3_event_PLUG_named.svg`
- `docs/figures/p3/p3_event_RIOT_alias.svg`
- `docs/figures/p3/p3_event_RIOT_named.svg`
- `docs/figures/p3/p3_event_VKTX_alias.svg`
- `docs/figures/p3/p3_event_VKTX_named.svg`
- `docs/figures/p3/p3_event_XXII_alias.svg`
- `docs/figures/p3/p3_event_XXII_named.svg`
