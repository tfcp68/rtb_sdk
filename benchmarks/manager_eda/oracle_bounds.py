#!/usr/bin/env python3
"""
Theoretical bounds of the 200-rate improvement at a fixed volume V (an oracle). Without real response codes:
the model "P(200) of a request ~ Beta(mean=s, concentration κ)"; small κ → requests differ strongly in P(200)
(there is something to choose from), large κ → all are similar (nothing to choose).

Computes for the send shares q = V/pool: E[p | top-q by p] (the oracle, knows p) and the ceiling of the "omniscient" (knows the outcome).
Result: docs/benchmark/manager_traffic/analysis/oracle_table.csv + figs/oracle_bounds.png
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "benchmark", "manager_traffic", "analysis")
S = 0.5                                   # the manager's current sellout according to the customer
KAPPAS = [1, 2, 5, 10, 30, 100]           # Beta concentration: α+β
QS = [0.5, 0.62, 0.8, 1.0]                # share of the pool sent to the manager (0.62 ≈ no_web_mobile/all in the logs)
PAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]


def top_q_mean(s: float, kappa: float, q: float) -> float:
    if q >= 1:
        return s
    a, b = s * kappa, (1 - s) * kappa
    thr = stats.beta.ppf(1 - q, a, b)
    # E[p·1{p>thr}] = s · P_{Beta(a+1,b)}(p>thr)
    return float(s * stats.beta.sf(thr, a + 1, b) / q)


rows = []
for k in KAPPAS:
    for q in QS:
        m = top_q_mean(S, k, q)
        rows.append({"kappa": k, "q": q, "oracle_p": m, "lift_pp": 100 * (m - S), "clairvoyant": min(1.0, S / q)})
df = pd.DataFrame(rows)
os.makedirs(os.path.join(OUT, "figs"), exist_ok=True)
df.to_csv(os.path.join(OUT, "oracle_table.csv"), index=False)

plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e4e3df",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "legend.frameon": False})
fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
for i, q in enumerate(QS[:3]):
    d = df[df["q"] == q]
    ax[0].plot(d["kappa"], 100 * d["oracle_p"], marker="o", color=PAL[i], label=f"send out {q:.0%} pool")
    ax[0].axhline(100 * min(1, S / q), color=PAL[i], linestyle=":", linewidth=1)
ax[0].axhline(100 * S, color="#52514e", linewidth=1)
ax[0].set_xscale("log"); ax[0].set_xlabel("κ = α+β (more → uniformity P(200))"); ax[0].set_ylabel("200-rate dispatched, %")
ax[0].set_title("oracle P(200) (solid) ceiling «know-how» (dotted)", fontsize=11); ax[0].legend(fontsize=8)
x = np.linspace(0.001, 1, 300)
for i, k in enumerate([2, 10, 100]):
    ax[1].plot(x, stats.beta.pdf(x, S * k, (1 - S) * k), color=PAL[i + 3], label=f"κ={k}")
ax[1].set_xlabel("P(200) request"); ax[1].set_title("Distribution P(200) upon request (mean 0.5)", fontsize=11); ax[1].legend()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "figs", "oracle_bounds.png"), dpi=130)
print(df.pivot(index="kappa", columns="q", values="oracle_p").round(3))
