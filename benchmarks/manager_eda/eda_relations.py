#!/usr/bin/env python3
"""
Relations between tags: region ↔ device, device/region/channel ↔ time of day, day of week, etc.

Continuation of eda_manager.py (same cache, markups and styling). Run after aggregate.py:
    python benchmarks/manager_eda/eda_relations.py
Result: docs/benchmark/manager_traffic/reports/relations_report.md + figs/r*.png + tables/r_*.csv

Relation measures: NMI = MI/min(H) unconditional and conditional at a fixed ep (VOD/Live), since much in the stream
is structurally determined by the traffic type. Specific "cells" (value A × value B) are found by lift and support.
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np
import pandas as pd
import polars as pl
from sklearn.cluster import KMeans

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eda_manager as E  # noqa: E402
from config import ALL_DEVICES, CACHE, PRIMARY_SEGMENT, REPORT, SEGMENTS  # noqa: E402
from eda_manager import PAL, INK, INK2, SURF, cond_nmi, fig_save, h, jsd, mi_nmi, p, pct, plt, seg, table  # noqa: E402

HX_TAGS = ["location", "channel", "category", "contractor", "client_version"]
AXES = ["device", "ep", "place", "position", "is_child", "hod", "dow", "location", "channel", "category", "contractor", "client_version"]
WEEKDAY_OF_DAY0 = 3  # 01.10.2026 — Thursday
WEEKEND_DAYS = {2, 3}  # Sat, Sun in the logs (03.10, 04.10)


def add_time(df: pd.DataFrame) -> pd.DataFrame:
    df["hod"] = (df["hour"] % 24).astype(int)
    df["day"] = (df["hour"] // 24).astype(int)
    df["dow"] = ((df["day"] + WEEKDAY_OF_DAY0) % 7).map(dict(enumerate(E.WD)))
    return df


def load_hx(tag: str) -> pd.DataFrame:
    parts = [pl.read_parquet(os.path.join(CACHE, f"hx_{tag}_d{i:02d}.parquet")) for i in range(E.n_days())]
    return add_time(E._norm(pl.concat(parts).to_pandas()))


def load_combo() -> pd.DataFrame:
    parts = [pl.read_parquet(os.path.join(CACHE, f"combo_d{i:02d}.parquet")) for i in range(E.n_days())]
    return E._norm(pl.concat(parts).to_pandas())


class Sources:
    """Sources of joint frequencies: for a pair of axes the first aggregate that has both columns is taken."""

    def __init__(self) -> None:
        self.cube = add_time(E.load_cube())
        self.hx = {t: load_hx(t) for t in HX_TAGS}
        self.hc = {t: E.load_hc(t) for t in ("location", "channel", "category", "contractor", "client_version")}
        self.combo = load_combo()
        self.srcs = [("cube", self.cube), *[(f"hx_{t}", d) for t, d in self.hx.items()], ("combo", self.combo),
                     *[(f"hc_{t}", d) for t, d in self.hc.items()]]

    def joint(self, a: str, b: str, segname: str) -> pd.DataFrame | None:
        for _, df in self.srcs:
            if a in df.columns and b in df.columns and "ep" in df.columns:
                q = seg(df, segname)
                cols = list(dict.fromkeys(["ep", a, b]))
                q = q[(q[a] != "") & (q[b] != "")]
                return q.groupby(cols, observed=True)["n"].sum().reset_index()
        return None


# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_matrix(S: Sources) -> pd.DataFrame:
    h(2, "1. Matrix of links between all tags")
    p(f"Segment `{PRIMARY_SEGMENT}`. Axis: {', '.join(AXES)} (`hod` — day-hour, `dow` — weekday). "
      "Two matrices: **unconditional NMI** and **conditional ep (VOD/Live)** — The second removes structural connections "
      "(the category is only VOD, channel only Live etc.p.). Couples, for which there is no joint table "
      "(counterparty × region), not counted.")
    n = len(AXES)
    M0, M1 = np.full((n, n), np.nan), np.full((n, n), np.nan)
    rows = []
    for (i, a), (j, b) in itertools.combinations(enumerate(AXES), 2):
        jt = S.joint(a, b, PRIMARY_SEGMENT)
        if jt is None or jt.empty:
            continue
        nmi0 = mi_nmi(jt, a, b)[1]
        nmi1 = np.nan if "ep" in (a, b) else cond_nmi(jt, a, b, ["ep"])[1]
        M0[i, j] = M0[j, i] = nmi0
        M1[i, j] = M1[j, i] = nmi1
        rows.append({"A": a, "B": b, "NMI": nmi0, "NMI upon ep": nmi1, "query": int(jt["n"].sum())})
    for M in (M0, M1):
        np.fill_diagonal(M, 1.0)
    fig, ax = plt.subplots(1, 2, figsize=(15, 6.4))
    for k, (M, ttl) in enumerate([(M0, "NMI (unconditional)"), (M1, "NMI heretofore ep (VOD/Live)")]):
        im = ax[k].imshow(M, cmap=E.SEQ, vmin=0, vmax=0.6); ax[k].grid(False)
        ax[k].set_xticks(range(n), AXES, rotation=45, ha="right"); ax[k].set_yticks(range(n), AXES)
        for i in range(n):
            for j in range(n):
                v = M[i, j]
                if np.isnan(v):
                    ax[k].text(j, i, "·", ha="center", va="center", color=INK2)
                elif i != j:
                    ax[k].text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5, color="white" if v > 0.35 else INK)
        ax[k].set_title(ttl)
    fig.colorbar(im, ax=ax, fraction=0.02)
    fig_save(fig, "r01_nmi_matrix", "Matrix NMI")
    t = pd.DataFrame(rows).sort_values("NMI upon ep", ascending=False)
    table(t, "r_pairs_nmi", md_rows=25, floatfmt=3)
    return t


def section_device_time(S: Sources) -> None:
    h(2, "2. Device ↔ time (hour, weekday)")
    c = S.cube
    # index = P(device | hod) / P(device)
    g = c.groupby(["device", "hod"])["n"].sum().unstack(fill_value=0).reindex(ALL_DEVICES)
    idx = (g / g.sum(0)) / (g.sum(1) / g.to_numpy().sum()).to_numpy()[:, None]
    fig, ax = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={"width_ratios": [1.3, 1]})
    im = ax[0].imshow(np.log2(idx.to_numpy(dtype=float)), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto"); ax[0].grid(False)
    ax[0].set_yticks(range(len(idx)), idx.index); ax[0].set_xticks(range(0, 24, 2)); ax[0].set_xlabel("hour")
    ax[0].set_title("Device: How many times his share in an hour is higher/below-average (log₂)")
    fig.colorbar(im, ax=ax[0], label="log₂ index (0 = averagely)")
    # normalized daily profiles (share of the daily volume by hour) — VOD/Live separately for major devices
    big = list(g.sum(1).sort_values(ascending=False).index[:6])
    for i, dv in enumerate(big):
        s = g.loc[dv] / g.loc[dv].sum()
        ax[1].plot(s.index, s.values * 100, color=PAL[i], label=dv)
    ax[1].set_xlabel("hour"); ax[1].set_ylabel("% day-to-day"); ax[1].set_title("Daily profile of large devices"); ax[1].legend(fontsize=7)
    fig_save(fig, "r10_device_hour", "Device × hour")

    rows = []
    wd = c.assign(we=c["day"].isin(WEEKEND_DAYS))
    for dv in ALL_DEVICES:
        s = g.loc[dv]
        q = wd[wd["device"] == dv]
        we = q[q["we"]]["n"].sum() / len(WEEKEND_DAYS)
        wk = q[~q["we"]]["n"].sum() / (E.n_days() - len(WEEKEND_DAYS))
        rows.append({"device": dv, "peak, hour": int(s.idxmax()), "night 00–06, %": 100 * s.loc[0:5].sum() / s.sum(), "evening 18–23, %": 100 * s.loc[18:23].sum() / s.sum(),
                     "peak/mine": s.max() / max(s.min(), 1), "weekend/weekday": we / wk})
    t = pd.DataFrame(rows).sort_values("evening 18–23, %", ascending=False)
    table(t, "r_device_time", floatfmt=3)
    # VOD / Live separately: evening share
    m = c.groupby(["ep", "hod"])["n"].sum().unstack(fill_value=0)
    p("Daily profiles VOD and Live markedly: "
      + "; ".join(f"{E.EP_RU[ep]} — peak {int(m.loc[ep].idxmax())}:00, nightly (00–06) {pct(m.loc[ep].loc[0:5].sum() / m.loc[ep].sum())}" for ep in m.index) + ".")
    # day of week × device
    dd = c.groupby(["device", "dow"])["n"].sum().unstack(fill_value=0)[E.WD[3:] + E.WD[:3]] if set(E.WD) <= set(c["dow"]) else None
    if dd is not None:
        sh = dd.div(dd.sum(0), axis=1)
        p("The share of the device in traffic by day of the week (in %, 7 daylight — one-day):")
        table((100 * sh.reindex(ALL_DEVICES)).round(2).reset_index(), "r_device_dow", floatfmt=3)


def section_location_device(S: Sources) -> None:
    h(2, "3. Region ↔ device")
    f = S.hc["location"]
    f = f[f["location"] != ""]
    segs = ("all", PRIMARY_SEGMENT)
    for sname in segs:
        q = seg(f, sname)
        tot = q.groupby("location")["n"].sum()
        top = tot.sort_values(ascending=False).index[:25]
        m = q[q["location"].isin(top)].groupby(["location", "device"])["n"].sum().unstack(fill_value=0)
        m = m[[d for d in ALL_DEVICES if d in m.columns]].reindex(top)
        sh = m.div(m.sum(1), axis=0)
        glob = q.groupby("device")["n"].sum()
        glob = glob / glob.sum()
        nmi = mi_nmi(q, "location", "device")
        p(f"`{sname}`: NMI(region, device) = **{nmi[1]:.3f}** (MI {nmi[0]:.3f} bit; H(device) = {nmi[3]:.2f}).")
        if sname == "all":
            fig, ax = plt.subplots(1, 2, figsize=(15, 6.4), gridspec_kw={"width_ratios": [1.2, 1]})
            im = ax[0].imshow(sh.to_numpy(), cmap=E.SEQ, vmin=0, vmax=1, aspect="auto"); ax[0].grid(False)
            ax[0].set_xticks(range(sh.shape[1]), sh.columns, rotation=40, ha="right"); ax[0].set_yticks(range(len(sh)), sh.index)
            ax[0].set_title("Percentage of devices in the region (top-25)", fontsize=11)
            dev = (sh / glob.reindex(sh.columns).to_numpy()).apply(np.log2)
            im2 = ax[1].imshow(dev.to_numpy(dtype=float), cmap="RdBu_r", vmin=-1.5, vmax=1.5, aspect="auto"); ax[1].grid(False)
            ax[1].set_xticks(range(dev.shape[1]), dev.columns, rotation=40, ha="right"); ax[1].set_yticks(range(len(dev)), dev.index)
            ax[1].set_title("log₂ deviation from the total share of the device", fontsize=11); fig.colorbar(im2, ax=ax[1])
            fig_save(fig, "r20_location_device", "Region × device")
        # regions with a special device mix
        big = tot[tot / tot.sum() >= 0.002].index
        rows = []
        mm = q[q["location"].isin(big)].groupby(["location", "device"])["n"].sum().unstack(fill_value=0)
        for loc, r in mm.iterrows():
            v = r.to_numpy(float)
            gv = glob.reindex(mm.columns).to_numpy()
            dom = mm.columns[int(np.argmax(v / v.sum() / gv))]
            rows.append({"location": loc, "traffic": tot[loc] / tot.sum(), "JSD generically, bit": jsd(v + 1e-9, gv * v.sum() + 1e-9),
                         "most «excess» device": dom, "its share in the region": float(r[dom] / v.sum()), "it’s": float(glob[dom])})
        t = pd.DataFrame(rows).sort_values("JSD generically, bit", ascending=False)
        MD = E.MD
        MD.append(f"Regions with the most atypical device composition (`{sname}`, ≥0.2% traffic):\n")
        table(t.head(12), f"r_location_device_{sname}", md_rows=12, floatfmt=3)


def section_location_time(S: Sources) -> None:
    h(2, "4. Region ↔ day-time")
    f = S.hx["location"]
    f = seg(f[f["location"] != ""], PRIMARY_SEGMENT)
    tot = f.groupby("location")["n"].sum()
    top = tot.sort_values(ascending=False).index[:60]
    m = f[f["location"].isin(top)].groupby(["location", "hod"])["n"].sum().unstack(fill_value=0).reindex(top)
    pr = m.div(m.sum(1), axis=0)
    glob = f.groupby("hod")["n"].sum()
    glob = glob / glob.sum()
    nmi = mi_nmi(f.groupby(["location", "hod"])["n"].sum().reset_index(), "location", "hod")
    p(f"NMI(region, hour) = **{nmi[1]:.4f}** (MI {nmi[0]:.4f} bit): The profile of the day in the regions is almost the same, if you look at it all at once; "
      "below — Which regions are different?. (Region codes undeciphered — These are identifiers from `location`.)")
    X = pr.to_numpy()
    km = KMeans(n_clusters=4, n_init=10, random_state=0).fit(X)
    order = np.argsort(km.labels_ * 100 + np.argmax(X, 1))
    fig, ax = plt.subplots(1, 2, figsize=(15, 6.4), gridspec_kw={"width_ratios": [1.3, 1]})
    im = ax[0].imshow((pr.iloc[order] / glob.to_numpy()).apply(np.log2).to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto"); ax[0].grid(False)
    ax[0].set_yticks(range(len(order)), pr.index[order], fontsize=6); ax[0].set_xticks(range(0, 24, 2)); ax[0].set_xlabel("hour")
    ax[0].set_title("Regions (top-60) cluster-wise: log₂ half-hour", fontsize=11)
    fig.colorbar(im, ax=ax[0])
    for k in range(4):
        sel = km.labels_ == k
        ax[1].plot(range(24), 100 * X[sel].mean(0), color=PAL[k], label=f"cluster {k + 1} ({sel.sum()} regions)")
    ax[1].plot(range(24), 100 * glob.to_numpy(), color=INK2, linestyle="--", label="region")
    ax[1].set_xlabel("hour"); ax[1].set_ylabel("% daily"); ax[1].set_title("Average cluster profiles", fontsize=11); ax[1].legend(fontsize=8)
    fig_save(fig, "r21_location_hour", "Region × hour")
    rows = []
    for i, loc in enumerate(pr.index):
        rows.append({"location": loc, "traffic": tot[loc] / tot.sum(), "cluster": int(km.labels_[i]) + 1, "peak, hour": int(np.argmax(X[i])),
                     "night 00–06, %": 100 * X[i][:6].sum(), "evening 18–23, %": 100 * X[i][18:].sum(),
                     "JSD generically, bit": jsd(X[i] + 1e-12, glob.to_numpy() + 1e-12)})
    t = pd.DataFrame(rows).sort_values("JSD generically, bit", ascending=False)
    table(t, "r_location_time", md_rows=15, floatfmt=3)
    spread = np.ptp(t["peak, hour"]), (t["night 00–06, %"].min(), t["night 00–06, %"].max())
    p(f"Spread of peak hour between regions: {int(spread[0])} ?; nocturnal (00–06) traffic — from {spread[1][0]:.1f}% until {spread[1][1]:.1f}%.")


def section_channel(S: Sources) -> None:
    h(2, "5. Channels and categories: time, device, region")
    f = S.hx["channel"]
    f = seg(f[f["channel"] != ""], PRIMARY_SEGMENT)
    tot = f.groupby("channel")["n"].sum().sort_values(ascending=False)
    top = tot.index[:40]
    m = f[f["channel"].isin(top)].groupby(["channel", "hod"])["n"].sum().unstack(fill_value=0).reindex(top)
    pr = m.div(m.sum(1), axis=0)
    order = pr.apply(lambda r: (r * np.arange(24)).sum(), axis=1).sort_values().index    # by the day's "center of mass"
    nmi = mi_nmi(f[f["channel"].isin(tot.index[:300])].groupby(["channel", "hod"])["n"].sum().reset_index(), "channel", "hod")
    p(f"NMI(channel, hour) topless-300 channel = **{nmi[1]:.3f}** (MI {nmi[0]:.3f} bit).")
    fig, ax = plt.subplots(1, 2, figsize=(15, 6.6), gridspec_kw={"width_ratios": [1.3, 1]})
    im = ax[0].imshow(pr.loc[order].to_numpy() * 100, cmap=E.SEQ, aspect="auto"); ax[0].grid(False)
    ax[0].set_yticks(range(len(order)), order, fontsize=6.5); ax[0].set_xticks(range(0, 24, 2)); ax[0].set_xlabel("hour")
    ax[0].set_title("Channels (top-40): % daily volume of requests by hour"); fig.colorbar(im, ax=ax[0])
    # channels ↔ device and channels ↔ region (combo)
    cb = seg(S.combo, PRIMARY_SEGMENT)
    cb = cb[(cb["channel"] != "") & (cb["location"] != "")]
    rows = []
    for ch in tot.index[:40]:
        q = cb[cb["channel"] == ch].groupby("location")["n"].sum()
        pq_ = (q / q.sum()).to_numpy()
        dv = f[f["channel"] == ch].groupby("device")["n"].sum()
        rows.append({"channel": ch, "traffic": tot[ch] / tot.sum(), "share-1 region": float(pq_.max()),
                     "efficient regions (exp H)": float(np.exp(-(pq_[pq_ > 0] * np.log(pq_[pq_ > 0])).sum())),
                     "dominant": dv.idxmax(), "share": float(dv.max() / dv.sum())})
    t = pd.DataFrame(rows)
    ax[1].scatter(t["traffic"] * 100, t["efficient regions (exp H)"], s=30, color=PAL[1])
    ax[1].set_xscale("log"); ax[1].set_yscale("log"); ax[1].set_xlabel("linkage, %"); ax[1].set_ylabel("regionally")
    ax[1].set_title("Channel regionality: few regions = regional")
    fig_save(fig, "r30_channel", "Channels")
    table(t.sort_values("efficient regions (exp H)").head(15), "r_channels_regionality", md_rows=15, floatfmt=3)
    reg = t[t["efficient regions (exp H)"] < 5]
    p(f"Top-40 channel «regional» (regionally < 5) were found {len(reg)}; "
      f"median number of effective regions — {t['efficient regions (exp H)'].median():.0f}.")
    # device ↔ channel
    nmi_d = mi_nmi(f[f["channel"].isin(tot.index[:300])].groupby(["channel", "device"])["n"].sum().reset_index(), "channel", "device")
    p(f"NMI(channel, device) = **{nmi_d[1]:.3f}**; NMI(region, channel) (Live, full-blown) = "
      f"**{mi_nmi(cb[cb['channel'].isin(tot.index[:300])].groupby(['location', 'channel'])['n'].sum().reset_index(), 'location', 'channel')[1]:.3f}**.")
    # categories
    h(3, "5.1 Categories (VOD) ↔ time and arrangement")
    fc = S.hx["category"]
    fc = seg(fc[fc["category"] != ""], PRIMARY_SEGMENT)
    ct = fc.groupby("category")["n"].sum().sort_values(ascending=False)
    topc = ct.index[:15]
    mc = fc[fc["category"].isin(topc)].groupby(["category", "hod"])["n"].sum().unstack(fill_value=0).reindex(topc)
    prc = mc.div(mc.sum(1), axis=0)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    im = ax.imshow(prc.to_numpy() * 100, cmap=E.SEQ, aspect="auto"); ax.grid(False)
    ax.set_yticks(range(len(topc)), topc); ax.set_xticks(range(0, 24, 2)); ax.set_xlabel("hour")
    ax.set_title("Categories VOD (top-15): % hourly"); fig.colorbar(im)
    fig_save(fig, "r31_category_hour", "Categories × hour")
    p(f"NMI(category, hour) = **{mi_nmi(fc.groupby(['category', 'hod'])['n'].sum().reset_index(), 'category', 'hod')[1]:.3f}**, "
      f"NMI(category, device) = **{mi_nmi(fc.groupby(['category', 'device'])['n'].sum().reset_index(), 'category', 'device')[1]:.3f}**.")


def section_weekend(S: Sources) -> None:
    h(2, "6. Weekdays and weekends: What is changing in the composition of traffic")
    p("Weekends in the lairs — Sat 03.10 and 04.10 (2 daylight), weekday — others 5. Estimate rough: one-set.")
    rows, tops = [], []
    for tag, df in [("device", S.cube), ("place", S.cube), ("position", S.cube)] + [(t, S.hx[t]) for t in HX_TAGS]:
        q = seg(df, PRIMARY_SEGMENT)
        q = q[q[tag] != ""]
        we = q[q["day"].isin(WEEKEND_DAYS)].groupby(tag)["n"].sum()
        wk = q[~q["day"].isin(WEEKEND_DAYS)].groupby(tag)["n"].sum()
        idx = we.index.union(wk.index)
        a, b = we.reindex(idx, fill_value=0).to_numpy(float), wk.reindex(idx, fill_value=0).to_numpy(float)
        rows.append({"tag": tag, "JSD weekend vs weekday, bit": jsd(a + 1e-9, b + 1e-9)})
        sh_a, sh_b = a / a.sum(), b / b.sum()
        for v, x, y in zip(idx, sh_a, sh_b):
            if max(x, y) >= 0.005 and y > 0:
                tops.append({"tag": tag, "value": v, "weekend": x, "weekday": y, "attitude": x / y})
    table(pd.DataFrame(rows).sort_values("JSD weekend vs weekday, bit", ascending=False), "r_weekend_jsd", floatfmt=3)
    t = pd.DataFrame(tops)
    t["_d"] = np.abs(np.log(t["attitude"]))
    t = t.sort_values("_d", ascending=False).drop(columns="_d")
    p("Meanings, Whose place in traffic changes the most on the weekend (share ≥0.5% at least one group):")
    table(t.head(15), "r_weekend_values", md_rows=15, floatfmt=3)


def section_cells(S: Sources, pairs: pd.DataFrame) -> None:
    h(2, "7. Specific «cell»: strongest connections of values")
    p("For couples with the greatest NMI upon ep discharged (value A × value B) supportive ≥ 0.2% Segment traffic and the largest |log lift|. "
      "lift > 1 — pairings are more common, < 1 — less.")
    rows = []
    for _, r in pairs.head(10).iterrows():
        a, b = r["A"], r["B"]
        jt = S.joint(a, b, PRIMARY_SEGMENT)
        if jt is None:
            continue
        g = jt.groupby([a, b])["n"].sum()
        N = g.sum()
        pa_, pb_ = g.groupby(level=0).sum() / N, g.groupby(level=1).sum() / N
        for (va, vb), n in g.items():
            s_ = n / N
            if s_ >= 0.002:
                rows.append({"A": f"{a}={va}", "B": f"{b}={vb}", "support": s_, "lift": s_ / (pa_[va] * pb_[vb]), "NMI pair": r["NMI upon ep"]})
    t = pd.DataFrame(rows)
    t["|log lift|"] = np.abs(np.log(t["lift"]))
    t = t.sort_values("|log lift|", ascending=False).drop(columns="|log lift|")
    table(t.head(40), "r_cells", md_rows=25, floatfmt=3)


def main() -> None:
    out = REPORT
    E.FIGS, E.TABLES = os.path.join(out, "figs"), os.path.join(out, "tables")
    os.makedirs(E.FIGS, exist_ok=True)
    os.makedirs(E.TABLES, exist_ok=True)
    E.MD = []
    # mark new files with the prefix r* so as not to collide with eda_report
    S = Sources()
    E.MD.append("# Links between tags: region, device, time, channels\n")
    p("> It’s about finding connections **downstream** (traffic), It’s not about selling: There are no manager response codes in the logs. "
      "But it is these connections that determine, What profiles exist at all and how distinguishable they are by behavior.")
    pairs = section_matrix(S)
    section_device_time(S)
    section_location_device(S)
    section_location_time(S)
    section_channel(S)
    section_weekend(S)
    section_cells(S, pairs)
    with open(os.path.join(out, "relations_report.md"), "w", encoding="utf-8") as fh:
        fh.write(E.privacy.markdown("\n".join(E.MD)))
    print("Report →", os.path.join(out, "relations_report.md"))


if __name__ == "__main__":
    main()
