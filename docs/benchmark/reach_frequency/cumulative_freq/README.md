# Cumulative frequency limits — Hypothesis 1 (summary report)

Local README for this folder. This is branch **D** of the general report
[`../README.md`](../README.md) — three consecutive stages (problem → gain on
logs → A/B on the balancer), each in its own `.md`. This file is navigation between them,
so you don't get confused about which report covers what.

## What was tested (in plain words)

A campaign has a daily per-user impression limit
(`user_frequency_limit.d = C`, e.g. "no more than 5 impressions per day to one person").
The balancer plans **each hour independently** and does not subtract what it has
already shown that user in previous hours — it spreads the daily volume proportionally to the traffic
`w_h` (which has an evening peak). Reality, however, is **front-loaded**: people use up their
limit over the course of the day and "drop off" — by evening their remainder is already small. The model therefore
overestimates the evening hours and underestimates the morning ones.

The question has three parts: **(1)** how large this error is, **(2)** how much of it
a cheap fix actually closes (without the exact per-user LP — it is `O(H×N×U)`, intractable),
**(3)** whether implementing it pays off on the real balancer.

## Three stages

| Stage | Question | Report | What was touched |
|---|---|---|---|
| **D. Problem** | How much does the model err against cumulative reality? | [`cumfreq_report.md`](cumfreq_report.md) | Nothing — microsimulation on logs |
| **D.1. Gain on logs** | What share of this error does a cheap approximation close? | [`fix_gain_report.md`](fix_gain_report.md) | Nothing — also a simulation on logs, no balancer code |
| **D.2. A/B on the balancer** | What does the fix deliver after real integration into the balancer? | [`hyp1_ab_report.md`](hyp1_ab_report.md) | Balancer (`seasonal/balance.py`, behind a flag) |

Each stage builds on the previous one but **does not automatically inherit its conclusion** —
the effect size at each step was recomputed and turned out smaller than
expected at the previous one (details in the results table below).

## Results by stage

| Stage | Metric | Result |
|---|---|---|
| D | `TV(prop,true)` — error in the shape of the hourly distribution | **7%** at limit 5, up to **12%** at tight 1–2, **4%** at loose 10. Verdict: **CONFIRMED** |
| D.1 | `gap_closed` — share of this error closed by the approximation on logs | **~50%** at typical limits C=3–10 (recommended approximation B); reference for A/B — **2–4 pp** |
| D.2 | Real `TV` gain after integration into the balancer (6-day prod profile) | **C=1–2 → 9.0 / 4.8 pp** (real effect, above the ~5% noise); **C≥5 → ≤0.9 pp** (within noise) |

**Why D.2 did not confirm the 2–4 pp reference from D.1.** `seasonality.py:86` builds an
hourly histogram without the date (`h = ts.hour`) — "7 requests in a single day" and "1 request
seven days in a row" are indistinguishable to the balancer. On a multi-day prod profile this
smears out precisely the user burst structure on which the fix's gain relies.
With tight limits (C=1–2) the fix survives this smearing; with loose ones (C≥5) it does
not. The detailed mechanism is in `hyp1_ab_report.md`, §3.3.

## Conclusions

1. **The problem is real** (D) and **the fix works** (D.1, D.2) — both stages are confirmed
   independently, including a bit-for-bit validation of the integration into the real balancer (D.2, §3.1).
2. **Fix A (elastic buffer) is rejected** — it strictly loses to fix B at any
   limit (D.1 and D.2 independently agree on this), requires calibrating an extra
   parameter `β`, and at loose limits does worse than doing nothing.
3. **Production payoff hinges on one unknown fact** — the distribution of
   `user_frequency_limit.d` across real campaigns. If limits of 1–3 dominate, implement the fix;
   if ≥5 dominate, the effect drowns in the model's own weekly noise (~5%).
   This is a cheap check against campaign configs, but it has not been done yet (the same gap as
   with fix 0, where the distribution of the scarcity `R` is likewise unknown).
4. **Both fixes (B and A) are implemented behind flags, off by default** — zero
   impact on prod until the flag is explicitly enabled.

## Folder files

**Stage D (problem):**
- [`test_cumfreq.ipynb`](test_cumfreq.ipynb) — microsimulation: sweep over the limit `C`, driver, decomposition, verdict
- [`cumfreq_report.md`](cumfreq_report.md) — full report (verdict CONFIRMED)

**Stage D.1 (gain on logs, balancer untouched):**
- [`measure_fix_gain.py`](measure_fix_gain.py) — gain measurement for two approximations (B — aggregated headroom, A — elastic buffer)
- [`fix_gain_report.md`](fix_gain_report.md) — report; raw run log — `fix_gain_output.txt` (local artifact, not included)

**Stage D.2 (A/B on the real balancer):**
- [`hyp1_ab_report.md`](hyp1_ab_report.md) — main A/B report (starts with "did it get better or worse")
- [`hyp1_ab_balancer.py`](hyp1_ab_balancer.py) — harness: real `build_seasonal_context` + slot loop, flag OFF vs ON
- [`make_ab_log.py`](make_ab_log.py) — downsamples the parquet to CSV for the harness (whole-user sampling, `hash(uid) % 187`)
- `ab_log_1day.csv` (local artifact, not included), `ab_log_3day.csv` (local artifact, not included), `ab_log_6day.csv` (local artifact, not included) — generated downsamples (1/3/6 days — sensitivity check for day-blending)
