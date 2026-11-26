# Hypothesis 1: measuring the GAIN from the fix

A continuation of [`cumfreq_report.md`](cumfreq_report.md). That report proved that the **problem is
real** (the `TV(prop,true)` gap = 7–12%), but honestly noted (lines 21–24): **the fix itself
was not measured**. Here we measure it — we apply two cheap approximations from section 1 of
[`frequency_accounting_improvements.md`](../../../frequency_accounting_improvements.md)
**on logs, without touching the balancer code**, and see what share of the gap each closes.

Script: [`measure_fix_gain.py`](measure_fix_gain.py). Data: the clean week
`janus-20260615` (27.7 million user-days, EmptyUser excluded). Metric:
`gap_closed = (TV(prop,true) − TV(fixed,true)) / TV(prop,true)`. `TV` normalizes both
curves to a sum of 1 → it is purely a **shape error**, volume drift does not interfere.

> **Verdict: the recommended fix (aggregated headroom) closes ~50% of the shape gap
> at typical limits (C=3–10), but barely helps at tight ones (C=1: 10%).
> The elastic buffer is the mirror image: it helps only at tight limits and hurts at loose ones.
> The remaining ~47% is irreducible user heterogeneity (a per-user LP is needed,
> and it is intractable). The real gain in prod will be even smaller — the `true` reference takes `P=1`
> (the campaign gets an impression on every user request until the limit is exhausted;
> in reality, competition with other campaigns/filters gives `P<1` — see
> `cumfreq_report.md`, §2).**
>
> **Update.** The fix has since been implemented and run through an A/B on the real balancer —
> see [`hyp1_ab_report.md`](hyp1_ab_report.md). The result is different: the effect split by
> limit tightness (not by the 2–4 pp reference below), and the B+A hybrid idea was closed — B
> wins at any limit.

Validation: the reproduced baseline `TV(prop,true)` = 0.119/0.101/0.088/0.070/0.044
for C=1/2/3/5/10 — matches the headline from `cumfreq_report.md` → the pipeline is correct.

---

## 1. What exactly was applied (two approximations from section 1)

**B — aggregated remaining headroom (recommended by the doc).** We walk through the hours 0→23
with a SHARED budget remainder `b`, starting at `C`. In each hour we deliver
`Σ_userdays min(req_uh, b)` over the **real hourly request histogram**, then
deplete `b -= delivered_h / N_userdays`. Front-loading arises adaptively. The difference
from `true`: in `true` each user carries **their own personal** `before`, here — a **shared
population** remainder. This difference is the irreducible remainder of the error.

**A — elastic buffer.** `prop[h] × (1 − h/24)^β`, a sweep over β. A pure heuristic on
time of day. For a fair shape comparison we renormalize to the same total `T`.

---

## 2. Result: the share of the shape gap closed

| `C` | `TV(prop,true)` | `TV(headroom)` | **closed (B)** | volume B / true | best β (A) | closed (A) |
|----:|----:|----:|----:|----:|:--:|----:|
| 1 | 0.1185 | 0.1063 | **10%** | 0.78× | 0.5 | **38%** |
| 2 | 0.1005 | 0.0743 | **26%** | 0.92× | 0.5 | 25% |
| 3 | 0.0875 | 0.0453 | **48%** | 0.96× | 0.5 | 4% |
| 5 | 0.0699 | 0.0330 | **53%** | 1.01× | 0.5 | −40% |
| 10 | 0.0435 | 0.0216 | **50%** | 1.09× | 0.5 | −180% |

**Read it as follows:**

- **Solution B** removes **~50% of the shape gap** at typical limits (C=3–10) and barely
  touches the total volume at C=5 (1.01×). At the tight C=1 it helps weakly (10%) and
  under-delivers volume (0.78×) — the shared headroom is depleted too sharply, the shape
  is over-front-loaded.
- **Solution A (elastic)** has a **mirror-image** usefulness profile: it helps only at
  tight limits (C=1: 38%, C=2: 25%), and at loose ones it **worsens** the shape (C=5: −40%,
  C=10: −180%). The reason: at a loose limit `true` is only slightly flatter than `prop`, rather than
  monotonically decreasing through the whole day as the curve `(1−h/24)^β` imposes. Also the raw volume
  drops to 0.33–0.62× (killing evening traffic).

---

## 3. Why ~47% remains (hourly curves, C=5)

`prop` overestimates the late hours and underestimates the early ones. `headroom` **fixes the morning
exactly** (h=0: 425k → exactly `true`), but **over-fixes the late evening**: by h=22–23 the shared
remainder is depleted, and the fix under-delivers (fixed 438k/393k vs true 521k/547k). The remainder
of the error is precisely the part where real users diverge in the time their limit is exhausted,
and a single shared `b` does not reproduce this. It could only be removed by an exact per-user
LP — it is `O(H×N×U)`, intractable (see section 1 of the doc).

---

## 4. Conclusions and recommendation

1. **The fix works, but the effect is half the size of the gap itself.** "The 7% problem" → what is
   really closable by a cheap approximation is **~3.5 pp** of shape at C=5. This is an **upper bound**:
   here P=1; at a real P<1 and the clamp of the balancer's total budget the gain will be even
   smaller.
2. **B and A complement each other by limit tightness.** Neither dominates everywhere.
   A sensible prod option is a **hybrid** (headroom as the base + an elastic squeeze at very
   tight per-user limits) or calibrating the switching threshold by `C` (section 6 of the doc).
3. **The order of implementation does not change:** implement B **behind a flag** + an A/B on the real
   `seasonal_balance_traffic` (as for fix 0), with a rule declared in advance. The expectation
   for the A/B is more modest than 7%: the reference is **2–4 pp** of shape accuracy for campaigns with a daily
   `user_frequency_limit`.

## 5. How to reproduce

```
.venv/Scripts/python.exe docs/benchmark/reach_frequency/cumulative_freq/measure_fix_gain.py
```

Env overrides: `PROFILE_FILE=E:/Logs/janus-XXXXXX.parquet`, `SAMPLE_DAYS=2` (a quick
logic check). A full run on the 8 GB parquet is a heavy window pass (minutes),
after which the sweep over `C` is cheap. The raw log is `fix_gain_output.txt` (local artifact, not included).
