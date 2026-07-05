"""One-off QA analysis over archived oos-main-v2 signals + raw decisions + snapshots.
CPU only, no GPU, no new GPU signal trials. Prints labelled blocks consumed by QA_ANSWERS.md.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agorasim.agents.personas import PersonaBank
from agorasim.agents.sim_prompts import read_jsonl
from agorasim.data.universe import parse_date
from agorasim.evals.prediction import information_coefficient as ic
from agorasim.evals.stylized_facts import stylized_fact_report
from agorasim.schemas import parse_decision
from scripts.p5_stats import forward_returns, momentum, ticker_closes

QA = Path("data/raw/qa")
SNAP = Path("data/snapshots/g1/oos")
TICKERS = ["NVNI", "TLRY", "EDIT", "CHPT", "BLNK", "FRSX", "TPET", "OGI", "CCO", "ICCM"]
MODEL_SEED = {"Qwen/Qwen2.5-1.5B-Instruct": 1337, "Qwen/Qwen2.5-3B-Instruct": 2337,
              "microsoft/Phi-3.5-mini-instruct": 3337}


def spearman(a, b):
    return ic(np.array(a), np.array(b))


def signals():
    return [r for r in read_jsonl(QA / "signals.jsonl") if not r.get("_summary")]


def paired(sig_key="imbalance_cw", h=5):
    closes = {tk: c for tk, c in ticker_closes(SNAP).items()}
    fwd = {tk: forward_returns(closes[tk], h) for tk in TICKERS}
    rows = []
    for r in signals():
        f = fwd.get(r["ticker"], {}).get(r["date"])
        if f is not None:
            rows.append((r["ticker"], r["date"], float(r[sig_key]), f))
    return rows  # (ticker, date, signal, fwd)


def day_block_boot_ic(rows, block=5, n=3000, seed=7):
    """Circular moving-block bootstrap resampling whole DAYS (all tickers of a day together)."""
    rng = np.random.default_rng(seed)
    by_date = defaultdict(list)
    for tk, d, s, f in rows:
        by_date[d].append((s, f))
    days = sorted(by_date)
    D = len(days)
    nb = int(np.ceil(D / block))
    out = []
    for _ in range(n):
        starts = rng.integers(0, D, nb)
        idx = np.concatenate([(np.arange(st, st + block) % D) for st in starts])[:D]
        s, f = [], []
        for j in idx:
            for sv, fv in by_date[days[j]]:
                s.append(sv); f.append(fv)
        out.append(spearman(s, f))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    print("### A. STATISTICAL ###")
    rows = paired("imbalance_cw", 5)
    s = [r[2] for r in rows]; f = [r[3] for r in rows]
    print(f"[A0] pooled 5d IC (cw) = {spearman(s, f):+.4f}  n={len(rows)}")
    print(f"[A1] day-blocked (whole-day) 95% CI = {day_block_boot_ic(rows)}")
    su = [(r[0], r[1], float(next(x['imbalance_uw'] for x in signals()
           if x['ticker']==r[0] and x['date']==r[1])), r[3]) for r in rows]
    print(f"[A1] day-blocked CI (uw) = {day_block_boot_ic(su)}")

    # A3 decomposition
    by_date = defaultdict(list); by_tk = defaultdict(list)
    for tk, d, sv, fv in rows:
        by_date[d].append((sv, fv)); by_tk[tk].append((sv, fv))
    xsec = [spearman([a for a, _ in v], [b for _, b in v]) for v in by_date.values() if len(v) >= 3]
    print(f"[A3] within-day cross-sectional mean IC = {np.mean(xsec):+.4f} "
          f"(sd {np.std(xsec):.3f}, n_days {len(xsec)}); "
          f"t={np.mean(xsec)/(np.std(xsec)/np.sqrt(len(xsec))):+.2f}")
    ts = {tk: spearman([a for a, _ in v], [b for _, b in v]) for tk, v in by_tk.items() if len(v) >= 5}
    print(f"[A3] per-ticker time-series IC: " + ", ".join(f"{k}:{v:+.2f}" for k, v in ts.items()))
    print(f"[A3] mean per-ticker TS IC = {np.mean(list(ts.values())):+.4f}")

    # A4 jackknife by ticker
    print("[A4] jackknife (drop-one) pooled 5d IC:")
    for drop in TICKERS:
        sub = [(sv, fv) for tk, d, sv, fv in rows if tk != drop]
        print(f"     -{drop}: {spearman([a for a,_ in sub],[b for _,b in sub]):+.4f}")

    # A5 dispersion
    arr = np.array([r[2] for r in rows])
    print(f"[A5] imbalance_cw: min {arr.min():+.3f} p25 {np.percentile(arr,25):+.3f} "
          f"med {np.median(arr):+.3f} mean {arr.mean():+.3f} p75 {np.percentile(arr,75):+.3f} "
          f"max {arr.max():+.3f}; %>0.9 = {100*np.mean(arr>0.9):.1f}%; %>0 = {100*np.mean(arr>0):.1f}%; "
          f"unique_vals={len(np.unique(arr))}")
    keep = [(sv, fv) for _, _, sv, fv in rows if sv <= 0.9]
    print(f"[A5] 5d IC on imbalance<=0.9 subsample (n={len(keep)}) = "
          f"{spearman([a for a,_ in keep],[b for _,b in keep]):+.4f}")

    # A6 confounds
    closes = ticker_closes(SNAP)
    mom5 = {tk: momentum(closes[tk], 5) for tk in TICKERS}
    trip = []  # (imbalance, fwd5, trailing5)
    for tk, d, sv, fv in rows:
        m = mom5.get(tk, {}).get(d)
        if m is not None:
            trip.append((sv, fv, m))
    imb = [a for a, _, _ in trip]; fwd5 = [b for _, b, _ in trip]; tr5 = [c for _, _, c in trip]
    r_mf = spearman(tr5, fwd5); r_if = spearman(imb, fwd5); r_it = spearman(imb, tr5)
    partial = (r_if - r_it * r_mf) / np.sqrt(max(1e-9, (1 - r_it**2) * (1 - r_mf**2)))
    print(f"[A6] 5d IC of trailing-5d momentum = {r_mf:+.4f}; reversal(-mom) = {-r_mf:+.4f}; "
          f"imbalance = {r_if:+.4f}; corr(imb,mom)={r_it:+.3f}; "
          f"partial rank corr(imb,fwd | mom) = {partial:+.4f}  (n={len(trip)})")

    # A7 DSR internals
    per_trial_sr = []
    for key in ("imbalance_cw", "imbalance_uw"):
        for h in (1, 5):
            rw = paired(key, h)
            ret = np.sign([r[2] for r in rw]) * np.array([r[3] for r in rw])
            ret = ret[np.isfinite(ret)]
            sr = ret.mean() / ret.std(ddof=1) * np.sqrt(252) if ret.std() > 0 else 0.0
            per_trial_sr.append(float(sr))
    print(f"[A7] per-(signal,horizon) sign-strategy SR = {[round(x,2) for x in per_trial_sr]}; "
          f"sr_var(input to DSR)={np.var(per_trial_sr):.4f}; n_trials=4 (from TRIALS.md)")

    print("\n### C. MECHANISM ###")
    raws = []
    for fp in (QA / "raw").glob("*.jsonl"):
        raws += read_jsonl(fp)
    dec = []  # (model, ticker, date, ai, AgentDecision)
    for rec in raws:
        p = parse_decision(rec.get("raw_text", ""))
        if p is None:
            continue
        rid = rec["request_id"].split("-")
        tk, arm, date, ai = rid[0], rid[1], "-".join(rid[2:5]), int(rid[5][1:])
        dec.append((rec["model"], tk, date, ai, p))
    print(f"[C12] parsed decisions: {len(dec)} of {len(raws)} raw")
    overall = Counter(d[4].action for d in dec)
    tot = sum(overall.values())
    print(f"[C12] overall action%: " + ", ".join(f"{k} {100*v/tot:.1f}%" for k, v in overall.items()))
    for m in MODEL_SEED:
        c = Counter(d[4].action for d in dec if d[0] == m); t = sum(c.values())
        print(f"       {m.split('/')[-1]}: " + ", ".join(f"{k} {100*c[k]/t:.1f}%" for k in ('buy','sell','hold')))
    # per persona style (map ai->style via that model's seed)
    banks = {m: PersonaBank(15, seed=sd).personas for m, sd in MODEL_SEED.items()}
    by_style = defaultdict(Counter)
    for m, tk, date, ai, p in dec:
        by_style[banks[m][ai].style][p.action] += 1
    print("[C12] action% by persona style:")
    for st, c in sorted(by_style.items()):
        t = sum(c.values())
        print(f"       {st:35s} buy {100*c['buy']/t:4.1f} sell {100*c['sell']/t:4.1f} hold {100*c['hold']/t:4.1f} (n={t})")
    # per-day decision entropy (Shannon, base-3 normalized), averaged
    byday = defaultdict(Counter)
    for m, tk, date, ai, p in dec:
        byday[(tk, date)][p.action] += 1
    ents = []
    for c in byday.values():
        t = sum(c.values()); ps = [c[a]/t for a in ('buy','sell','hold') if c[a] > 0]
        ents.append(-sum(pp*np.log(pp) for pp in ps) / np.log(3))
    print(f"[C12] per-(ticker,day) decision entropy (norm base-3): mean {np.mean(ents):.3f} "
          f"median {np.median(ents):.3f} min {np.min(ents):.3f} max {np.max(ents):.3f}  (NEW: not previously computed)")

    # C17 per-model imbalance (buy-sell tilt on that model's own decisions)
    print("[C17] per-model mean signed action (buy=+1,sell=-1,hold=0):")
    for m in MODEL_SEED:
        v = [(+1 if d[4].action=='buy' else -1 if d[4].action=='sell' else 0) for d in dec if d[0]==m]
        print(f"       {m.split('/')[-1]}: mean {np.mean(v):+.3f} median {np.median(v):+.0f} "
              f"buy_frac {np.mean([x>0 for x in v]):.2f}")

    # C15 news counts per ticker-day (point-in-time, matching sim: news created_at<=asof)
    print("[C15] news items visible per ticker-day (<= asof):")
    dates_used = sorted({d for _, d in byday})
    zero = tot_days = 0
    per_tk_news = {}
    for tk in TICKERS:
        news = read_jsonl(SNAP / tk / "news.jsonl")
        counts = []
        for d in sorted({dd for (t, dd) in byday if t == tk}):
            cut = parse_date(d)
            k = sum(1 for n in news if (n.get('created_at') or n.get('updated_at'))
                    and parse_date(n.get('created_at') or n.get('updated_at')) <= cut)
            counts.append(k); tot_days += 1
            if k == 0: zero += 1
        per_tk_news[tk] = (np.mean(counts) if counts else 0, np.min(counts) if counts else 0)
    print("       " + ", ".join(f"{tk}:mean{v[0]:.0f}/min{v[1]}" for tk, v in per_tk_news.items()))
    print(f"[C15] ticker-days with ZERO visible news = {zero}/{tot_days} = {100*zero/tot_days:.1f}%")

    # C16 alias integrity: does any visible headline name the real ticker?
    print("[C16] alias leak: ticker-days whose visible news mentions the real ticker symbol:")
    leak = tot2 = 0
    for tk in TICKERS:
        news = read_jsonl(SNAP / tk / "news.jsonl")
        for d in sorted({dd for (t, dd) in byday if t == tk}):
            cut = parse_date(d)
            head = " ".join(str(n.get('headline') or n.get('summary') or '') for n in news
                            if (n.get('created_at') or n.get('updated_at'))
                            and parse_date(n.get('created_at') or n.get('updated_at')) <= cut)
            tot2 += 1
            if tk.lower() in head.lower():
                leak += 1
    print(f"       {leak}/{tot2} = {100*leak/tot2:.1f}% contain the ticker symbol in headline text")

    print("\n### D19 / D20 / E24 ###")
    # D19 AR(1) + naive logistic baselines (CPU, registered trial 4)
    ar_s, ar_f = [], []
    for tk in TICKERS:
        c = ticker_closes(SNAP)[tk]
        f1 = forward_returns(c, 1)
        px = dict(c)
        dts = sorted(f1)
        for i in range(1, len(dts)):
            prev = f1.get(dts[i-1]); cur = f1.get(dts[i])
            if prev is not None and cur is not None:
                ar_s.append(prev); ar_f.append(cur)
    print(f"[D19] AR(1): IC(r_t, r_t+1) = {spearman(ar_s, ar_f):+.4f}  n={len(ar_s)}; "
          f"hit={np.mean(np.sign(ar_s)==np.sign(ar_f)):.3f}")

    # D20 stylized facts on auction paths
    print("[D20] stylized facts on oos-main-v2 call-auction price paths:")
    sig = signals()
    for tk in TICKERS:
        rws = sorted((r for r in sig if r['ticker'] == tk), key=lambda r: r['date'])
        px = np.array([r['auction_price'] for r in rws], float)
        vol = np.array([r['auction_volume'] for r in rws], float)
        rr = np.diff(px) / px[:-1]
        rep = stylized_fact_report(rr, vol[1:])
        print(f"       {tk}: kurt {rep['excess_kurtosis']:+.2f} acf_r1 {rep['acf_r_lag1']:+.2f} "
              f"acf|r|1 {rep['acf_abs_r_lag1']:+.2f} corr(V,|r|) {rep.get('corr_volume_absr', float('nan')):+.2f}")

    # E24 missing / zero-volume bars per ticker over the used window
    print("[E24] snapshot bar quality over the run window (used decision days):")
    used_days = sorted({d for _, d in byday})
    for tk in TICKERS:
        bars = {b['t'][:10]: b for b in read_jsonl(SNAP / tk / 'bars_1d.jsonl')}
        tk_days = sorted({dd for (t, dd) in byday if t == tk})
        miss = sum(1 for d in tk_days if d not in bars)
        zerov = sum(1 for d in tk_days if d in bars and float(bars[d].get('v', 0)) == 0)
        print(f"       {tk}: decision_days {len(tk_days)} missing_bar {miss} zero_volume {zerov}")


if __name__ == "__main__":
    main()
