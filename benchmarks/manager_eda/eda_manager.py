#!/usr/bin/env python3
"""
EDA of the traffic going to the manager (a "black box" returning 200 / 2xx).

IMPORTANT: the logs have NO response codes and no "went to the manager" flag → everything below is an analysis of the INCOMING
traffic under markups by device_type (see config.SEGMENTS). The EDA claims nothing about the manager's
sellout; it describes which regularities the stream itself has (what can be predicted,
which segments to cut by, where users repeat, etc.).

Order:  prepare.py → aggregate.py → eda_manager.py
Result: docs/benchmark/manager_traffic/reports/eda_report.md + figs/*.png + tables/*.csv
"""
from __future__ import annotations

import sys as _privacy_sys
from pathlib import Path as _PrivacyPath
_privacy_sys.path.insert(0, str(_PrivacyPath(__file__).resolve().parents[2]))
from benchmarks import report_privacy as privacy

import argparse
import datetime as dt
import glob
import os
import sys

import matplotlib
from cycler import cycler

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import polars as pl  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (ALL_DEVICES, CACHE, DEV_IDX, EP_RU, HIGH_CARD, PRIMARY_SEGMENT, REPORT,  # noqa: E402
                    SEGMENTS, TAGS)
import aggregate as agg  # noqa: E402

# ── styling (palette from the dataviz skill, fixed order) ───────────────────────────────
PAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "figure.dpi": 100,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.titlecolor": INK, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "lines.linewidth": 2, "font.size": 10, "legend.frameon": False, "axes.prop_cycle": cycler(color=PAL),
})
SEQ = "Blues"

FIGS: str
TABLES: str
MD: list[str] = []
T0_DATE = dt.date(2026, 10, 1)   # logs T0 = 00:00 MSK 2026-10-01
WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def day_label(d: int) -> str:
    x = T0_DATE + dt.timedelta(days=d)
    return f"{x:%d.%m} {WD[x.weekday()]}"


def fig_save(fig, name: str, caption: str = "") -> None:
    privacy.figure(fig)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, name + ".png"), dpi=130)
    plt.close(fig)
    MD.append(f"![{caption or name}](figs/{name}.png)\n")


def table(df: pd.DataFrame, name: str, md_rows: int = 30, floatfmt: int = 3, index: bool = False) -> None:
    df = privacy.dataframe(df)
    df.to_csv(os.path.join(TABLES, name + ".csv"), index=index)
    d = df.head(md_rows).copy()
    if index:
        d = d.reset_index()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: f"{v:.{floatfmt}g}" if pd.notna(v) else "")
    MD.append("| " + " | ".join(map(str, d.columns)) + " |")
    MD.append("|" + "---|" * len(d.columns))
    for r in d.itertuples(index=False):
        MD.append("| " + " | ".join(str(x) for x in r) + " |")
    if len(df) > md_rows:
        MD.append(f"\n_(shown {md_rows} of {len(df)}; full-sheet: `tables/{name}.csv`)_")
    MD.append("")


def h(level: int, text: str) -> None:
    MD.append("\n" + "#" * level + " " + text + "\n")


def p(text: str) -> None:
    MD.append(text + "\n")


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


# ── loading the cache ─────────────────────────────────────────────────────────────────────────────
def n_days() -> int:
    return len(glob.glob(os.path.join(CACHE, "gaps_d*.npz")))


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    """Value cleaning: the typo 'swithroll', the case of broadcast_type."""
    if "place" in df:
        df["place"] = df["place"].replace({"swithroll": "switchroll"})
    if "broadcast" in df:
        df["broadcast"] = df["broadcast"].str.lower()
    for column in privacy.FIELDS.intersection(df.columns):
        privacy.register(df[column].dropna().unique())
    return df


def load_cube() -> pd.DataFrame:
    parts = []
    for i in range(n_days()):
        d = pl.read_parquet(os.path.join(CACHE, f"cube_d{i:02d}.parquet"))
        parts.append(d.with_columns(pl.lit(i).alias("day")))
    return _norm(pl.concat(parts).to_pandas())


def load_hc(tag: str) -> pd.DataFrame:
    parts = []
    for i in range(n_days()):
        d = pl.read_parquet(os.path.join(CACHE, f"hc_{tag}_d{i:02d}.parquet"))
        parts.append(d.with_columns(pl.lit(i).alias("day")))
    return _norm(pl.concat(parts).to_pandas())


def seg(df: pd.DataFrame, name: str) -> pd.DataFrame:
    return df[df["device"].isin(SEGMENTS[name])]


def nz(s: pd.Series, empty: str = "∅") -> pd.Series:
    return s.replace("", empty)


# ── information metrics ────────────────────────────────────────────────────────────────────
def mi_nmi(df: pd.DataFrame, a: str, b: str, w: str = "n") -> tuple[float, float, float, float]:
    """(MI bits, NMI=MI/min(H), H(a), H(b)); df is an aggregate with weight n."""
    t = df.groupby([a, b], observed=True)[w].sum().unstack(fill_value=0).to_numpy(dtype=float)
    N = t.sum()
    if N == 0 or t.shape[0] < 2 or t.shape[1] < 2:
        return 0.0, 0.0, 0.0, 0.0
    pxy = t / N
    px, py = pxy.sum(1, keepdims=True), pxy.sum(0, keepdims=True)
    nzm = pxy > 0
    mi = float((pxy[nzm] * np.log2(pxy[nzm] / (px @ py)[nzm])).sum())
    hx = float(-(px[px > 0] * np.log2(px[px > 0])).sum())
    hy = float(-(py[py > 0] * np.log2(py[py > 0])).sum())
    m = min(hx, hy)
    return mi, (mi / m if m > 0 else 0.0), hx, hy


def cond_nmi(df: pd.DataFrame, a: str, b: str, strata: list[str]) -> tuple[float, float]:
    """Conditional information I(a;b | strata) and its share of H(a | strata). Removes "structural" relations:
    e.g. place↔ep, where ep uniquely determines the allowed placements."""
    mi_s = h_s = tot = 0.0
    for _, g in df.groupby(strata, observed=True):
        w = float(g["n"].sum())
        mi, _, ha, _ = mi_nmi(g, a, b)
        mi_s += w * mi
        h_s += w * ha
        tot += w
    return (mi_s / tot, mi_s / h_s if h_s > 0 else 0.0)


def jsd(p_: np.ndarray, q_: np.ndarray) -> float:
    p_, q_ = p_ / p_.sum(), q_ / q_.sum()
    m = 0.5 * (p_ + q_)

    def kl(a, b):
        z = a > 0
        return float((a[z] * np.log2(a[z] / b[z])).sum())

    return 0.5 * kl(p_, m) + 0.5 * kl(q_, m)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. Overview
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_overview(cube: pd.DataFrame) -> None:
    h(2, "1. Overview of flow and marking")
    nd = cube["day"].nunique()
    tot = cube["n"].sum()
    p(f"Period: {nd} daylight ({day_label(0)} … {day_label(nd - 1)}), time — MSK. Total valid requests "
      f"(famous device_type, VOD/Live): **{tot:,}** (≈{tot / nd / 1e6:.1f} million/days).")
    p("**Markups (query):**")
    for k in ("all", "no_web_mobile"):
        p(f"- `{k}`: {', '.join(SEGMENTS[k])}")
    p("- `dev:<DEVICE>`: each type of device (tables below).")
    p(f"Detailed schedules are being built for `{PRIMARY_SEGMENT}`, excepted.")

    g = cube.groupby(["device", "ep"])["n"].sum().unstack(fill_value=0)
    g = g.reindex(ALL_DEVICES).fillna(0)
    t = pd.DataFrame({
        "device": g.index, "VOD/days": (g.get("avod", 0) / nd).round().astype(int), "Live/days": (g.get("alive", 0) / nd).round().astype(int),
    })
    t["fraction"] = (g.sum(1) / tot).values
    t["live-share"] = (g.get("alive", 0) / g.sum(1).replace(0, np.nan)).values
    t["no_web_mobile"] = ["✓" if d in SEGMENTS["no_web_mobile"] else "—" for d in t["device"]]
    table(t.sort_values("fraction", ascending=False), "overview_devices", floatfmt=3)
    sh = {k: cube[cube["device"].isin(SEGMENTS[k])]["n"].sum() / tot for k in ("all", "no_web_mobile")}
    p(f"Share of traffic in markup `no_web_mobile`: **{pct(sh['no_web_mobile'])}** from all valid requests. "
      "If, by agreement, the manager leaves ~50% current volume, The markup is close to reality; "
      "noticeably more/less — You need to adjust the list of devices in `config.py`.")

    # Fig 01: volume by day
    top = list(t.sort_values("fraction", ascending=False)["device"][:7])
    d = cube.assign(dg=np.where(cube["device"].isin(top), cube["device"], "other")).groupby(["day", "dg"])["n"].sum().unstack(fill_value=0) / 1e6
    d = d[top + (["other"] if "other" in d else [])]
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1.6, 1]})
    bottom = np.zeros(len(d))
    for i, c in enumerate(d.columns):
        ax[0].bar(range(len(d)), d[c], bottom=bottom, color=PAL[i % 8] if c != "other" else "#9a9a96", label=c, width=0.78, edgecolor=SURF, linewidth=1.5)
        bottom += d[c].to_numpy()
    ax[0].set_xticks(range(len(d)), [day_label(i) for i in d.index])
    ax[0].set_ylabel("millions of requests"); ax[0].set_title("Requests by day and device")
    ax[0].legend(ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    s = cube.assign(m=cube["device"].isin(SEGMENTS["no_web_mobile"]) * cube["n"]).groupby("day").agg(m=("m", "sum"), n=("n", "sum"))
    ax[1].plot(range(len(s)), s["m"] / s["n"], marker="o", color=PAL[0])
    ax[1].set_ylim(0, 1); ax[1].set_xticks(range(len(s)), [day_label(i) for i in s.index], rotation=45, ha="right")
    ax[1].set_title("Share `no_web_mobile` traffic")
    fig_save(fig, "f01_volume_by_day", "Volume per day")

    # Fig 02/03: daily and weekly profiles
    c = cube.assign(hod=cube["hour"] % 24)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    for i, (name, q) in enumerate([("all", c), ("no_web_mobile", seg(c, "no_web_mobile"))]):
        pr = q.groupby("hod")["n"].sum() / nd / 1e3
        ax[0].plot(pr.index, pr.values, color=PAL[i], label=name)
    ax[0].set_title("Profile of day (thousand. requests/hour, day-average)"); ax[0].set_xlabel("hour"); ax[0].legend()
    q = seg(c, "no_web_mobile")
    for i, ep in enumerate(["avod", "alive"]):
        pr = q[q["ep"] == ep].groupby("hod")["n"].sum() / nd / 1e3
        ax[1].plot(pr.index, pr.values, color=PAL[i + 2], label=EP_RU[ep])
    ax[1].set_title("`no_web_mobile`: VOD vs Live"); ax[1].set_xlabel("hour"); ax[1].legend()
    fig_save(fig, "f02_hour_profile", "Daily profile")

    q = seg(cube, "no_web_mobile").groupby("hour")["n"].sum()
    q = q.reindex(range(nd * 24), fill_value=0).to_numpy().reshape(nd, 24) / 1e3
    fig, ax = plt.subplots(figsize=(11, 3.8))
    im = ax.imshow(q, aspect="auto", cmap=SEQ)
    ax.set_yticks(range(nd), [day_label(i) for i in range(nd)]); ax.set_xticks(range(0, 24, 2)); ax.set_xlabel("hour"); ax.grid(False)
    fig.colorbar(im, label="thousand. requests/hour"); ax.set_title("`no_web_mobile`: hourly (days × hour)")
    fig_save(fig, "f03_hour_x_day", "Days×hour")
    # peak/trough
    pr = seg(c, "no_web_mobile").groupby("hod")["n"].sum() / nd
    p(f"Daily amplitude `no_web_mobile`: peak {int(pr.idxmax())}:00 MSK ({pr.max() / 1e3:.0f} thousand./hour), "
      f"minimum {int(pr.idxmin())}:00 ({pr.min() / 1e3:.0f} thousand./hour), peak/minimum = {pr.max() / max(pr.min(), 1):.1f}×.")

    # has_cid
    hc = cube.groupby(["device", "has_cid"])["n"].sum().unstack(fill_value=0)
    hc["shareless client_id"] = hc.get(False, 0) / hc.sum(1)
    p("Percentage of requests **without client_id** (user replaced by IP — on user graphs such requests are excluded):")
    table(hc[["shareless client_id"]].reset_index().sort_values("shareless client_id", ascending=False), "no_cid_by_device")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. Tags and their frequencies
# ══════════════════════════════════════════════════════════════════════════════════════════════
def tag_frame(cube: pd.DataFrame, hcs: dict, tag: str) -> pd.DataFrame:
    """A unified view (day, device, ep, place, <tag>, n) for any tag."""
    if tag in hcs:
        return hcs[tag]
    cols = list(dict.fromkeys(["day", "device", "ep", "place", tag]))
    return cube.groupby(cols, as_index=False)["n"].sum()


def section_tags(cube: pd.DataFrame, hcs: dict) -> None:
    h(2, "2. Tag frequencies")
    p("`∅` — parameter is not present in the request. Coverage = query, wherein.")
    # coverage by device
    tags = ["place", "position", "location", "category", "channel", "contractor", "is_child", "age", "broadcast", "client_version"]
    cov = {}
    for t in tags:
        f = tag_frame(cube, hcs, t)
        g = f.assign(has=f[t] != "").assign(w=lambda x: x["has"] * x["n"]).groupby("device")[["w", "n"]].sum()
        cov[t] = (g["w"] / g["n"])
    cv = pd.DataFrame(cov).reindex(ALL_DEVICES)
    fig, ax = plt.subplots(figsize=(11, 5))
    im = ax.imshow(cv.to_numpy(dtype=float), cmap=SEQ, vmin=0, vmax=1, aspect="auto"); ax.grid(False)
    ax.set_xticks(range(len(tags)), tags, rotation=40, ha="right"); ax.set_yticks(range(len(cv)), cv.index)
    for i in range(cv.shape[0]):
        for j in range(cv.shape[1]):
            v = cv.iat[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{100 * v:.0f}", ha="center", va="center", fontsize=7.5, color="white" if v > 0.55 else INK)
    fig.colorbar(im, label="covering"); ax.set_title("Coverage of parameters, % requests (device × parameter)")
    fig_save(fig, "f10_coverage", "Tag coverage")
    table(cv.reset_index().rename(columns={"index": "device"}), "tag_coverage_by_device", floatfmt=2)

    # cardinality and tails in the main segment
    h(3, f"2.1 Cardinal and «tails» (`{PRIMARY_SEGMENT}`)")
    rows, fig_tail = [], plt.subplots(1, 2, figsize=(13, 4.2))
    fig, ax = fig_tail
    for ti, tag in enumerate(["location", "category", "channel", "contractor", "client_version"]):
        f = seg(tag_frame(cube, hcs, tag), PRIMARY_SEGMENT)
        f = f[f[tag] != ""]
        v = f.groupby(tag)["n"].sum().sort_values(ascending=False)
        if v.empty:
            continue
        cs = v.cumsum() / v.sum()
        rows.append({"tag": tag, "unique": len(v), "tagged": int(v.sum()),
                     "top1": v.iloc[0] / v.sum(), "top10": cs.iloc[min(9, len(cs) - 1)], "top100": cs.iloc[min(99, len(cs) - 1)],
                     "valence 50%": int((cs < 0.5).sum() + 1), "on 90%": int((cs < 0.9).sum() + 1), "on 99%": int((cs < 0.99).sum() + 1)})
        ax[0].plot(np.arange(1, len(cs) + 1), cs.values, label=tag, color=PAL[ti])
        ax[1].loglog(np.arange(1, len(v) + 1), v.values / v.sum(), label=tag, color=PAL[ti])
    ax[0].set_xscale("log"); ax[0].set_xlabel("number (descendingly)"); ax[0].set_ylabel("stockpile")
    ax[0].set_title("Concentration: How many values cover the traffic"); ax[0].legend(fontsize=8)
    ax[1].set_xlabel("rank"); ax[1].set_ylabel("share"); ax[1].set_title("rang–frequency (log–log, Zipf?)")
    fig_save(fig, "f11_tags_tail", "Tails tagged")
    table(pd.DataFrame(rows), "tag_cardinality", floatfmt=3)

    # top values
    h(3, f"2.2 Top values (`{PRIMARY_SEGMENT}`)")
    for tag in ["place", "position", "location", "channel", "category", "contractor", "client_version", "is_child", "age", "broadcast"]:
        f = seg(tag_frame(cube, hcs, tag), PRIMARY_SEGMENT)
        v = f.groupby(tag)["n"].sum().sort_values(ascending=False)
        t = pd.DataFrame({tag: nz(pd.Series(v.index)).values, "requests/days": (v.values / cube["day"].nunique()).round().astype(int), "share": v.values / v.sum()})
        MD.append(f"**{TAGS.get(tag, tag)}** (`{tag}`) — top-12:\n")
        table(t.head(12), f"top_{tag}", md_rows=12, floatfmt=3)

    # placement × device
    h(3, "2.3 ad_place_type and ad_position")
    f = tag_frame(cube, hcs, "place")
    f = f.assign(place=nz(f["place"]))
    m = f.groupby(["device", "place"])["n"].sum().unstack(fill_value=0).reindex(ALL_DEVICES).fillna(0)
    sh = m.div(m.sum(1), axis=0)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    im = ax[0].imshow(sh.to_numpy(), cmap=SEQ, vmin=0, vmax=1, aspect="auto"); ax[0].grid(False)
    ax[0].set_xticks(range(sh.shape[1]), sh.columns, rotation=30, ha="right"); ax[0].set_yticks(range(sh.shape[0]), sh.index)
    for i in range(sh.shape[0]):
        for j in range(sh.shape[1]):
            ax[0].text(j, i, f"{100 * sh.iat[i, j]:.0f}", ha="center", va="center", fontsize=7.5, color="white" if sh.iat[i, j] > 0.55 else INK)
    ax[0].set_title("Share ad_place_type inside, %")
    q = seg(cube, PRIMARY_SEGMENT)
    q = q.assign(place=nz(q["place"]), position=nz(q["position"]))
    pm = q.groupby(["place", "position"])["n"].sum().unstack(fill_value=0)
    pm = pm.loc[:, pm.sum().sort_values(ascending=False).index[:8]]
    pm = pm.div(pm.sum(1), axis=0)
    im = ax[1].imshow(pm.to_numpy(), cmap=SEQ, vmin=0, vmax=1, aspect="auto"); ax[1].grid(False)
    ax[1].set_xticks(range(pm.shape[1]), pm.columns); ax[1].set_yticks(range(pm.shape[0]), pm.index)
    for i in range(pm.shape[0]):
        for j in range(pm.shape[1]):
            ax[1].text(j, i, f"{100 * pm.iat[i, j]:.0f}", ha="center", va="center", fontsize=8, color="white" if pm.iat[i, j] > 0.55 else INK)
    ax[1].set_title(f"`{PRIMARY_SEGMENT}`: ad_position inside ad_place_type, %")
    fig_save(fig, "f12_place", "ad_place_type")
    table((m.div(m.sum(1), axis=0).reset_index()), "place_by_device", floatfmt=3)

    # category vs channel: mutual exclusion
    h(3, "2.4 Category and channel: mutual exclusion")
    cmb = _norm(pl.concat([pl.read_parquet(os.path.join(CACHE, f"combo_d{i:02d}.parquet")) for i in range(n_days())]).to_pandas())
    cm = seg(cmb, PRIMARY_SEGMENT)
    cm = cm.assign(cat=cm["category"] != "", ch=cm["channel"] != "", loc=cm["location"] != "")
    x = cm.groupby(["ep", "cat", "ch"])["n"].sum().unstack(["cat", "ch"], fill_value=0)
    x = x.div(x.sum(1), axis=0)
    x.columns = [f"cat={int(a)},ch={int(b)}" for a, b in x.columns]
    table(x.rename(index=EP_RU).reset_index(), "cat_vs_channel", floatfmt=3)
    p("If `cat=1,ch=1` ≈ 0 — Category and channel do not appear in the same request (VOD category, Live — channel): "
      "campaign, targetable, will not receive any traffic.")
    return cmb  # type: ignore[return-value]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. Dependencies between tags and ad_place
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_dependencies(cube: pd.DataFrame, hcs: dict) -> None:
    h(2, "3. Dependencies between tags (NMI) and the verdict ad_place_type")
    p("NMI = MI / min(H) ∈ [0,1]: 0 — independent, 1 — One tag clearly defines the other. "
      "Threshold of practical significance adopted **0.05** (on tens of millions of lines, any MI statistically «meaningfully», "
      "magnitude of effect).")
    q = seg(cube, PRIMARY_SEGMENT)
    lows = ["device", "ep", "place", "position", "is_child", "age", "broadcast"]
    M = pd.DataFrame(np.nan, index=lows, columns=lows)
    for a in lows:
        for b in lows:
            M.loc[a, b] = 1.0 if a == b else mi_nmi(q, a, b)[1]
    fig, ax = plt.subplots(figsize=(7, 5.6))
    im = ax.imshow(M.to_numpy(dtype=float), cmap=SEQ, vmin=0, vmax=1); ax.grid(False)
    ax.set_xticks(range(len(lows)), lows, rotation=40, ha="right"); ax.set_yticks(range(len(lows)), lows)
    for i in range(len(lows)):
        for j in range(len(lows)):
            v = M.iat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color="white" if v > 0.55 else INK)
    fig.colorbar(im); ax.set_title(f"NMI mid-tag (`{PRIMARY_SEGMENT}`)")
    fig_save(fig, "f20_nmi_low", "NMI")

    # place vs everything: unconditional and conditional (within device×ep)
    rows = []
    strata = ["device", "ep"]
    base = seg(cube, PRIMARY_SEGMENT)
    h_place = mi_nmi(base, "place", "device")[2]
    mi_dev_ep = mi_nmi(base.assign(de=base["device"] + "|" + base["ep"]), "place", "de")[0]
    p(f"How much information `ad_place_type` already contained in a bundle *device × type (VOD/Live)*: "
      f"I(place; device,ep) = {mi_dev_ep:.2f} batter H(place) = {h_place:.2f} bit (**{pct(mi_dev_ep / h_place)}**).")
    cands = {"position": base, "is_child": base, "age": base, "broadcast": base,
             "hour": base.assign(hour=base["hour"] % 24)}
    for name, frame in cands.items():
        col = name
        mi, ratio = cond_nmi(frame, "place", col, strata)
        mi0, nmi0, _, _ = mi_nmi(frame, "place", col)
        rows.append({"with": name, "NMI unconditional": nmi0, "I(place;X | device,ep), bit": mi, "share H(place | device,ep)": ratio})
    for tag in ["location", "category", "channel", "contractor", "client_version"]:
        f = seg(hcs[tag], PRIMARY_SEGMENT)
        f = f[f[tag] != ""]
        mi, ratio = cond_nmi(f, "place", tag, strata)
        mi0, nmi0, _, _ = mi_nmi(f, "place", tag)
        rows.append({"with": tag, "NMI unconditional": nmi0, "I(place;X | device,ep), bit": mi, "share H(place | device,ep)": ratio})
    pv = pd.DataFrame(rows).sort_values("share H(place | device,ep)", ascending=False)
    table(pv, "place_nmi", floatfmt=3)
    p("«Share H(place | device,ep)» — How much of the remaining uncertainty `ad_place_type` (after the device is known, and VOD/Live) "
      "tagging X. This is a test of the hidden patterns: unconditional NMI overflow.")
    strong = pv[pv["share H(place | device,ep)"] >= 0.05]
    top = pv.iloc[0]
    if strong.empty:
        verdict = (f"Verdict: **after taking into account the device and VOD/Live at `ad_place_type` There are no significant dependencies** "
                   f"(maximum {top['share H(place | device,ep)']:.3f} s `{top['with']}` < 0.05 threshold 0.05). "
                   "As an independent axis of markup, it does not add a signal beyond `device × ep`: regularity, apparently, no. "
                   "It’s the flow structure; liaison P(200) — only with response codes.")
    else:
        verdict = (f"Verdict: after taking into account the device and VOD/Live at `ad_place_type` dependency (≥ 0.05 residual entropy): "
                   + ", ".join(f"`{r['with']}` ({r['share H(place | device,ep)']:.2f})" for _, r in strong.iterrows()) +
                   ". These are the structural connections of flow; liaison P(200) You can’t say without answer codes.")
    p(verdict)
    q = base
    hq = q.assign(hod=q["hour"] % 24)

    # place by hour
    fig, ax = plt.subplots(figsize=(10, 4))
    hp = hq.assign(place=nz(hq["place"])).groupby(["hod", "place"])["n"].sum().unstack(fill_value=0)
    hp = hp.div(hp.sum(1), axis=0)
    bottom = np.zeros(len(hp))
    for i, c in enumerate(hp.columns):
        ax.bar(hp.index, hp[c], bottom=bottom, color=PAL[i % 8], label=c, width=0.85, edgecolor=SURF, linewidth=1)
        bottom += hp[c].to_numpy()
    ax.set_xlabel("hour"); ax.set_ylabel("share"); ax.set_title(f"Composition ad_place_type clockwise (`{PRIMARY_SEGMENT}`)")
    ax.legend(ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.15))
    fig_save(fig, "f21_place_by_hour", "place clockwise")

    # high-cardinality tags vs device/ep/place
    rows = []
    for tag in HIGH_CARD:
        f = seg(hcs[tag], PRIMARY_SEGMENT)
        f = f[f[tag] != ""]
        for other in ("device", "ep", "place"):
            if tag == "ua" and other == "device":
                pass
            rows.append({"tag": tag, "with": other, "NMI": mi_nmi(f, tag, other)[1]})
    t = pd.DataFrame(rows).pivot(index="tag", columns="with", values="NMI")
    p("NMI high-cardinal tags with device / ep / place (higher, more tagged «determined» device/type):")
    table(t.reset_index(), "nmi_highcard", floatfmt=2)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. Stability over time and predictability
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_stability(cube: pd.DataFrame, hcs: dict) -> None:
    h(2, "4. Day stability and predictability")
    nd = cube["day"].nunique()
    rows = []
    for tag in ["device", "place", "position", "location", "category", "channel", "contractor", "client_version"]:
        f = seg(tag_frame(cube, hcs, tag), PRIMARY_SEGMENT)
        f = f[f[tag] != ""]
        pv = f.groupby([tag, "day"])["n"].sum().unstack(fill_value=0)
        seen = set()
        for d in range(nd):
            others = pv.drop(columns=d).sum(1).to_numpy(float)
            cur = pv[d].to_numpy(float)
            new_share = float(pv[d][~pv.index.isin(seen)].sum() / max(cur.sum(), 1)) if d else np.nan
            rows.append({"tag": tag, "day": day_label(d), "d": d, "JSD for the rest of the day (bit)": jsd(cur + 1e-12, others + 1e-12),
                         "traffic ratio, never seen before": new_share})
            seen |= set(pv.index[pv[d] > 0])
    st = pd.DataFrame(rows)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    for i, tag in enumerate(st["tag"].unique()):
        s = st[st["tag"] == tag]
        ax[0].plot(s["d"], s["JSD for the rest of the day (bit)"], marker="o", color=PAL[i % 8], label=tag)
        ax[1].plot(s["d"][1:], s["traffic ratio, never seen before"][1:], marker="o", color=PAL[i % 8], label=tag)
    ax[0].set_title("JSD daytime (below — more stable)"); ax[0].set_xticks(range(nd), [day_label(d) for d in range(nd)], rotation=45, ha="right")
    ax[1].set_title("Share of traffic on values, past-day"); ax[1].set_xticks(range(nd), [day_label(d) for d in range(nd)], rotation=45, ha="right")
    ax[0].legend(fontsize=7, ncol=2)
    fig_save(fig, "f30_stability", "Tag stability")
    s = st.groupby("tag").agg(JSD=("JSD for the rest of the day (bit)", "mean"), new=("traffic ratio, never seen before", "mean"))
    table(s.reset_index().rename(columns={"JSD": "middle-class JSD, bit", "new": "middle-weight «new» value"}), "stability_tags", floatfmt=3)

    # volume predictability
    h(3, "4.1 Predictability of hourly volume")
    res = []
    fig, ax = plt.subplots(figsize=(11, 4))
    for si, sname in enumerate(["no_web_mobile", "all"]):
        v = seg(cube, sname).groupby("hour")["n"].sum().reindex(range(nd * 24), fill_value=0).to_numpy(float).reshape(nd, 24)
        e1 = np.abs(v[1:] - v[:-1]) / v[1:]
        pred2 = np.array([v[:d].mean(0) for d in range(2, nd)])
        e2 = np.abs(v[2:] - pred2) / v[2:]
        res.append({"segment": sname, "MAPE «yesterday»": float(e1.mean()), "MAPE «past-day average»": float(e2.mean()),
                    "MAPE «yesterday» (days 3..)": float(e1[1:].mean())})
        ax.plot(v.reshape(-1) / 1e3, color=PAL[si], label=sname)
    ax.set_xticks(range(0, nd * 24, 24), [day_label(d) for d in range(nd)]); ax.set_ylabel("thousand. requests/hour")
    ax.set_title("Hourly traffic volume"); ax.legend()
    fig_save(fig, "f31_hourly_volume", "Hourly volume")
    table(pd.DataFrame(res), "volume_predictability", floatfmt=3)
    p("MAPE — Error of the simplest forecasts of hourly volume. Importance of order 5–10% signifier, what "
      "quota «80% traffic manager» You can plan on the profile of the past days without a complex model; "
      "weekend/holiday profile (in 7 day only one weekend — roughing-up).")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. Tag combinations ("request profiles")
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_combos(cmb_all: pd.DataFrame) -> None:
    h(2, "5. Request profiles (tagging): How many are they and how stable are they?")
    nd = n_days()
    parts = []
    for i in range(nd):
        d = _norm(pl.read_parquet(os.path.join(CACHE, f"combo_d{i:02d}.parquet")).to_pandas())
        parts.append(d.assign(day=i))
    cmb = seg(pd.concat(parts), PRIMARY_SEGMENT)
    keys = {
        "device+ep+place": ["device", "ep", "place"],
        "+region": ["device", "ep", "place", "location"],
        "+region+category": ["device", "ep", "place", "location", "category"],
        "+region+channel": ["device", "ep", "place", "location", "channel"],
        "full-fledged (region+category+channel)": ["device", "ep", "place", "location", "category", "channel"],
    }
    rows = []
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
    for ki, (kn, cols) in enumerate(keys.items()):
        g = cmb.groupby(cols + ["day"])["n"].sum().reset_index()
        tot = g.groupby(cols)["n"].sum().sort_values(ascending=False)
        cs = tot.cumsum() / tot.sum()
        seen_share = []
        seen = set()
        for d in range(nd):
            gd = g[g["day"] == d]
            idx = pd.MultiIndex.from_frame(gd[cols]) if len(cols) > 1 else pd.Index(gd[cols[0]])
            if d:
                seen_share.append(float(gd["n"][~idx.isin(seen)].sum() / gd["n"].sum()))
            seen |= set(idx)
        rows.append({"key": kn, "weekly": len(tot), "on 50% traffic": int((cs < .5).sum() + 1), "on 90%": int((cs < .9).sum() + 1),
                     "on 99%": int((cs < .99).sum() + 1), "Wed. traffic «new» profile (days 2+)": float(np.mean(seen_share))})
        ax[0].plot(np.arange(1, len(cs) + 1), cs.values, color=PAL[ki], label=kn)
    ax[0].set_xscale("log"); ax[0].set_xlabel("profile (descendingly)"); ax[0].set_ylabel("stockpile")
    ax[0].set_title("Traffic concentration by profile"); ax[0].legend(fontsize=7)
    t = pd.DataFrame(rows)
    ax[1].barh(t["key"], t["Wed. traffic «new» profile (days 2+)"], color=PAL[1], height=0.55)
    ax[1].set_title("Traffic on «new» profile (share)", fontsize=11); ax[1].invert_yaxis()
    fig_save(fig, "f40_combos", "Combinations")
    table(t, "combos_summary", floatfmt=3)
    p("The fewer profiles are covered 90% traffic and less traffic «new» profile, The better the training works «probability 200 profiled» "
      "history (bandit/profilesheet). Big tail of new profiles — needed backoff coarsely.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. Users
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_users() -> None:
    h(2, "6. Users (only requests from client_id)")
    nd = n_days()
    us = [pl.read_parquet(os.path.join(CACHE, f"users_d{i:02d}.parquet")).with_columns(pl.lit(i).alias("day")) for i in range(nd)]
    dev_names = np.array(ALL_DEVICES + [""] * (32 - len(ALL_DEVICES)))
    seg_dev_idx = [DEV_IDX[d] for d in SEGMENTS[PRIMARY_SEGMENT]]
    prim = [u.filter(pl.col("dev").is_in(seg_dev_idx)) for u in us]
    allu = pl.concat(prim)
    pdf = allu.to_pandas()
    pdf["device"] = dev_names[pdf["dev"].to_numpy()]

    # daily uniques and distributions
    g = pdf.groupby(["day", "device"]).agg(users=("user", "size"), reqs=("n", "sum")).reset_index()
    dau = g.groupby("day")[["users", "reqs"]].sum()
    p(f"`{PRIMARY_SEGMENT}`, user/days (s client_id): "
      + ", ".join(f"{day_label(d)}: {int(v):,}" for d, v in dau["users"].items()) + ".")
    p(f"Requests per user per day: mean {dau['reqs'].sum() / dau['users'].sum():.2f}.")
    # percentiles per device
    rows = []
    for dv, q in pdf.groupby("device"):
        n = q["n"].to_numpy()
        rows.append({"device": dv, "benefit.-days": len(q), "mean": n.mean(), "p50": np.percentile(n, 50), "p90": np.percentile(n, 90),
                     "p99": np.percentile(n, 99), "max": n.max(), "share. s 1 request": float((n == 1).mean()),
                     "session/days (mean)": float(q["n_sess"].mean())})
    table(pd.DataFrame(rows).sort_values("benefit.-days", ascending=False), "users_per_day_stats", floatfmt=3)

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    bins = np.unique(np.round(np.logspace(0, 3.5, 40)).astype(int))
    top_devs = pdf.groupby("device").size().sort_values(ascending=False).index[:6]
    for i, dv in enumerate(top_devs):
        hist, _ = np.histogram(pdf.loc[pdf["device"] == dv, "n"], bins=bins)
        ax[0].plot(bins[:-1], hist / hist.sum(), color=PAL[i], label=dv)
    ax[0].set_xscale("log"); ax[0].set_yscale("log"); ax[0].set_xlabel("user requests per day"); ax[0].set_ylabel("share-days")
    ax[0].set_title("Distribution of requests per user"); ax[0].legend(fontsize=7)
    # Lorenz
    n = np.sort(pdf["n"].to_numpy())[::-1].astype(float)
    cs = np.cumsum(n) / n.sum()
    xs = np.arange(1, len(n) + 1) / len(n)
    ax[1].plot(xs[::max(1, len(xs) // 2000)], cs[::max(1, len(xs) // 2000)], color=PAL[0])
    ax[1].plot([0, 1], [0, 1], color=GRID, linestyle="--")
    ax[1].set_xlabel("share (most active)"); ax[1].set_ylabel("query"); ax[1].set_title("Lorentz curve: heavy-handed")
    heavy = {f"top {q}%": float(cs[int(len(n) * q / 100) - 1]) for q in (0.1, 1, 10)}
    # week
    wk = allu.group_by("user").agg(pl.col("n").sum().alias("n"), pl.len().alias("days"))
    dist = wk["days"].value_counts().sort("days").to_pandas()
    ax[2].bar(dist["days"], dist["count"] / dist["count"].sum(), color=PAL[2], width=0.7)
    ax[2].set_xlabel("how many days 7 user"); ax[2].set_ylabel("share"); ax[2].set_title("Regularity of the audience")
    fig_save(fig, "f50_users", "Users")
    p("Concentration of requests: " + ", ".join(f"{k} user {pct(v)} requests" for k, v in heavy.items()) + ".")
    wd = wk.to_pandas()
    p(f"Unique Users in a Week: **{len(wd):,}**; active 1 day: {pct((wd['days'] == 1).mean())}, "
      f"≥5 days: {pct((wd['days'] >= 5).mean())}. Requests from users, active ≥5 days: {pct(wd.loc[wd['days'] >= 5, 'n'].sum() / wd['n'].sum())}.")
    bots = pdf[pdf["n"] >= 2000]
    p(f"Suspicion of bots/general client_id: user-days ≥2000 day-by-day — {len(bots):,} "
      f"({pct(bots['n'].sum() / pdf['n'].sum())} requests).")
    md = pdf[pdf["n_dev"] > 1]
    p(f"Users, employed >1 `device_type` day: {pct(len(md) / len(pdf))} user-days.")

    # returning
    h(3, "6.1 Returns: «We’ve already seen this user»")
    seen = np.array([], dtype=np.uint32)
    rows = []
    for d in range(nd):
        u = prim[d]
        arr = u["user"].to_numpy()
        n = u["n"].to_numpy()
        if d:
            m = np.isin(arr, seen)
            rows.append({"day": day_label(d), "user": len(arr), "share. seen before": float(m.mean()),
                         "Percentage of requests from previously seen": float(n[m].sum() / n.sum())})
        seen = np.union1d(seen, arr)
    t = pd.DataFrame(rows)
    table(t, "user_returning", floatfmt=3)
    p("A high percentage of requests from already seen users means, User Features can be used online "
      "(history, How many times has the user been sent to the manager?) — This is the basis for frequency strategies.")

    # rank within the day, intervals, sessions
    h(3, "6.2 Intervals between requests and ranks in the day")
    G = [np.load(os.path.join(CACHE, f"gaps_d{i:02d}.npz")) for i in range(nd)]
    sumk = lambda k: sum(g[k] for g in G)  # noqa: E731
    di = np.array(seg_dev_idx)
    gl, glin, rk, sl = sumk("gap_log2")[di].sum(0), sumk("gap_lin")[di].sum(0), sumk("rank")[di].sum(0), sumk("sess_len")[di].sum(0)

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
    for ei, ep in enumerate(("avod", "alive")):
        x = gl[ei] / max(gl[ei].sum(), 1)
        ax[0].bar(np.arange(len(x)) + (ei - 0.5) * 0.4, x, width=0.4, color=PAL[ei + 2], label=EP_RU[ep])
    ax[0].set_xticks(range(0, 22, 3), [f"{2 ** i}s" if 2 ** i < 3600 else f"{2 ** i // 3600}?" for i in range(0, 22, 3)])
    ax[0].set_title("Interval to trail. request (log2)", fontsize=11); ax[0].legend()
    for ei, ep in enumerate(("avod", "alive")):
        x = glin[ei] / max(glin[ei].sum(), 1)
        ax[1].plot(np.arange(len(x)) * 10 / 60, x, color=PAL[ei + 2], label=EP_RU[ep])
    ax[1].set_yscale("log"); ax[1].set_xlabel("minutes"); ax[1].set_title("Interval < 1 ? (step 10 c, log)", fontsize=11); ax[1].legend()
    for ei, ep in enumerate(("avod", "alive")):
        x = rk[ei] / max(rk[ei].sum(), 1)
        ax[2].semilogy(np.arange(1, len(x)), x[:-1], color=PAL[ei + 2], label=f"{EP_RU[ep]} (share 60+: {x[-1]:.0%})")
    ax[2].set_xlabel("serial number of the user’s request per day"); ax[2].set_title("Daily query rank", fontsize=11); ax[2].legend(fontsize=8)
    fig_save(fig, "f51_gaps_ranks", "Intervals and ranks")

    rows = []
    for ei, ep in enumerate(("avod", "alive")):
        x = gl[ei] / max(gl[ei].sum(), 1)
        rows.append({"type": EP_RU[ep], "≤1 c": x[0], "1–15 c": x[1:4].sum(), "16–63 c": x[4:6].sum(), "1–17 mine": x[6:10].sum(),
                     "17 mine–1.2 ?": x[10:12].sum(), "> 1.2 ?": x[12:].sum()})
    table(pd.DataFrame(rows), "gap_shares", floatfmt=3)
    # peaks of the linear histogram
    for ei, ep in enumerate(("avod", "alive")):
        x = glin[ei].astype(float)
        sm = np.convolve(x, np.ones(3) / 3, mode="same")
        pk = [i for i in range(2, len(sm) - 2) if sm[i] > sm[i - 1] and sm[i] >= sm[i + 1] and sm[i] > 1.3 * np.median(sm[max(0, i - 12):i + 12])]
        pk = sorted(pk, key=lambda i: -sm[i])[:6]
        p(f"{EP_RU[ep]}: spacing (mine): " + (", ".join(f"{i * 10 / 60:.1f}" for i in sorted(pk)) if pk else "not found") + ".")
    cum = rk / np.maximum(rk.sum(1, keepdims=True), 1)
    rows = [{"type": EP_RU[ep], "rank=1 (first-day)": cum[ei][0], "rank 2–5": cum[ei][1:5].sum(), "rank 6–20": cum[ei][5:20].sum(),
             "rank 21+": cum[ei][20:].sum()} for ei, ep in enumerate(("avod", "alive"))]
    table(pd.DataFrame(rows), "rank_shares", floatfmt=3)
    ss = sl / np.maximum(sl.sum(1, keepdims=True), 1)
    rows = [{"type": EP_RU[ep], "1 request": ss[ei][0], "2–3": ss[ei][1:3].sum(), "4–10": ss[ei][3:10].sum(), "11+": ss[ei][10:].sum()}
            for ei, ep in enumerate(("avod", "alive"))]
    p(f"Session = user-request ≤ {agg.SESSION_GAP // 60} mine.")
    table(pd.DataFrame(rows), "session_shares", floatfmt=3)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7. Candidates for "companies": segments with excess concentration
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_segments_lift(cube: pd.DataFrame, hcs: dict) -> None:
    h(2, "7. Reconstruction «company»: What’s possible with these logs?")
    p("Manager companies (targeting, price, limit) **Query Logs cannot be Recovered**: The request does not contain information about, "
      "Which company won it and whether it won it at all?. Maximum, What’s driving traffic?, — find out *natural segments*: pairing "
      "tagging, which are more frequent, more independent than (lift > 1). It is for such segments usually "
      "target. Actual recovery is only possible with response codes (centimetre. section 9).")
    q = seg(cube, PRIMARY_SEGMENT)
    N = q["n"].sum()
    rows = []
    # low-card pairs
    q2 = q.assign(**{c: nz(q[c]) for c in ["place", "position", "is_child", "age", "broadcast"]})
    lows = ["device", "ep", "place", "position", "is_child", "age", "broadcast"]
    marg = {c: q2.groupby(c)["n"].sum() / N for c in lows}
    for i, a in enumerate(lows):
        for b in lows[i + 1:]:
            j = q2.groupby([a, b])["n"].sum() / N
            for (va, vb), s in j.items():
                if s >= 0.005:
                    rows.append({"A": f"{a}={va}", "B": f"{b}={vb}", "support": s, "lift": s / (marg[a][va] * marg[b][vb])})
    # device × high-card
    for tag in ["location", "channel", "category", "contractor", "client_version"]:
        f = seg(hcs[tag], PRIMARY_SEGMENT)
        f = f[f[tag] != ""]
        Nt = f["n"].sum()
        j = f.groupby(["device", tag])["n"].sum()
        mt = f.groupby(tag)["n"].sum() / Nt
        md_ = f.groupby("device")["n"].sum() / Nt
        for (dv, v), s in j.items():
            s2 = s / Nt
            if s2 >= 0.003:
                rows.append({"A": f"device={dv}", "B": f"{tag}={v}", "support": s2 * Nt / N, "lift": s2 / (md_[dv] * mt[v])})
    t = pd.DataFrame(rows)
    t = t[(t["lift"] > 1.5) | (t["lift"] < 0.5)].sort_values("support", ascending=False)
    table(t.head(60), "lift_pairs", md_rows=25, floatfmt=3)
    p("`lift > 1` — pairings occur more often than random, `< 1` — less (nearly incompatible). List — Candidates for segmentation in the strategy section.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 8. Comparing markups
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_segments_compare(cube: pd.DataFrame) -> None:
    h(2, "8. Comparison of markings (per device)")
    nd = cube["day"].nunique()
    rows = []
    for name, devs in SEGMENTS.items():
        q = cube[cube["device"].isin(devs)]
        if q.empty:
            continue
        n = q["n"].sum()
        rows.append({
            "marking": name, "requests/days (million)": n / nd / 1e6, "share": n / cube["n"].sum(),
            "live-share": q.loc[q["ep"] == "alive", "n"].sum() / n,
            "fraction place": q.loc[q["place"] != "", "n"].sum() / n,
            "fraction client_id": q.loc[q["has_cid"], "n"].sum() / n,
            "peak/day-by-day": (lambda s: s.max() / max(s.min(), 1))(q.groupby(q["hour"] % 24)["n"].sum()),
        })
    table(pd.DataFrame(rows), "segments_compare", md_rows=40, floatfmt=3)
    p("The manager’s quota is given in the share (for example 80%) or absolutely — chart, how many requests/days "
      "gives every markup, to compare with the arrangement.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 9. Ideas: what is missing and what to add
# ══════════════════════════════════════════════════════════════════════════════════════════════
def section_ideas() -> None:
    h(2, "9. What else is worth doing? / What kind of data is needed")
    p("""**We need data (lock-in):**
1. HTTP-managerial-code (200 / 2xx) on every request, gone + response time/timeout. It’s impossible without it: rate P(200) segmentally, predictor 200, reinstate the behavior of companies, oracle.
2. Identification «left the manager / left us» — let alone `device_type`.
3. If possible: price/CPM The winning company (If the manager gives it away) and any titles of the answer.

**What can be added to EDA, when the codes come:**
- Calibration curve P(200) profiled (device×place×region×hour); confidence interval, cross-country-stability.
- Addiction P(200) frequencywise: serial number of the user’s request per day/weekday, interval from the previous request, past 200 user (campaign-fulfillment/frequency limit of the manager).
- drift P(200) day-by-day/weekdays; bursts (Manager’s Flight Campaigns Included/turn off — You can see it like steps P(200) segmentally).
- oracle: centimetre. separate document.
- Couples (tagging → 200) tree/GBM interpretively (SHAP), find «targeting» company manager.
- Experiment: randomized holdout (1–2% segment traffic) optimised — The only way to get an unbiased estimate P(200) post-optimizer.""")


# ══════════════════════════════════════════════════════════════════════════════════════════════
def main() -> None:
    global FIGS, TABLES
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=REPORT)
    a = ap.parse_args()
    FIGS, TABLES = os.path.join(a.out, "figs"), os.path.join(a.out, "tables")
    os.makedirs(FIGS, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)
    if n_days() == 0:
        raise SystemExit("No cache: launch aggregate.py")

    cube = load_cube()
    hcs = {t: load_hc(t) for t in HIGH_CARD}

    MD.append("# EDA traffic for the manager (black-box 200 / 2xx)\n")
    p("> **Data limitation.** In the lairs `janus-*.parquet` No manager response codes and no indication «request went to the manager». "
      "That’s why EDA *entering* flow-marking `device_type`; everything, concerning sellout/P(200), postponed to new dens (section 9).")
    section_overview(cube)
    cmb = section_tags(cube, hcs)
    section_dependencies(cube, hcs)
    section_stability(cube, hcs)
    section_combos(cmb)
    section_users()
    section_segments_lift(cube, hcs)
    section_segments_compare(cube)
    section_ideas()
    with open(os.path.join(a.out, "eda_report.md"), "w", encoding="utf-8") as fh:
        fh.write(privacy.markdown("\n".join(MD)))
    print("Report →", os.path.join(a.out, "eda_report.md"))


if __name__ == "__main__":
    main()
