"""
One "seller": a set of companies + the full filter chain + best_price winner selection.

The same logic as in `log_benchmark/engine_full.run_algorithm` (sliding ad/user windows via `until`,
min_interval on the user×ad pair, volume as a hard limit), but as an object with a `serve(t, u, c)`
method: the stand needs several independent auctions in one stream (the hidden manager and our own
companies). Equivalence with run_algorithm(best_price) is checked by verify_seller.py.
"""
from __future__ import annotations

from array import array

INF = 1 << 60


class Seller:
    def __init__(self, pack, match: list[tuple]):
        self.pack = pack
        self.match = match
        A = pack.n
        self.cpm = pack.cpm
        self.end = pack.end_s
        self.until = list(pack.start_s)
        self.cnt = [0] * A
        self.adts = [array("i") for _ in range(A)]
        self.u_flag = [bool(pack.user_lims[a]) or pack.min_interval[a] > 0 for a in range(A)]
        self.u_keep = [max([l for l, _ in pack.user_lims[a]] + [1]) for a in range(A)]
        self.K = 1 << max(1, (A - 1).bit_length())
        self.udict: dict[int, list] = {}
        self.impressions = [0] * A
        self.revenue = 0.0
        self.requests = 0
        self.miss_nomatch = 0
        self.miss_filtered = 0

    @property
    def total_impressions(self) -> int:
        return sum(self.impressions)

    def serve(self, t: int, u: int, c: int) -> int:
        """Index of the winning company or -1."""
        self.requests += 1
        cand = self.match[c]
        if not cand:
            self.miss_nomatch += 1
            return -1
        until, end, u_flag, udict, K = self.until, self.end, self.u_flag, self.udict, self.K
        ok = []
        for a in cand:
            if t < until[a] or t >= end[a]:
                continue
            if u_flag[a]:
                st = udict.get(u * K + a)
                if st is not None and (t < st[0] or t < st[1]):
                    continue
            ok.append(a)
        if not ok:
            self.miss_filtered += 1
            return -1
        w = ok[0] if len(ok) == 1 else max(ok, key=self.cpm.__getitem__)

        pack = self.pack
        self.impressions[w] += 1
        self.revenue += self.cpm[w]
        self.cnt[w] += 1
        lst = self.adts[w]
        lst.append(t)
        nb = pack.start_s[w]
        if self.cnt[w] >= pack.volume[w]:
            nb = INF
        else:
            nl = len(lst)
            for lim, win in pack.ad_lims[w]:
                if nl >= lim:
                    x = lst[nl - lim] + win
                    if x > nb:
                        nb = x
        until[w] = nb
        if u_flag[w]:
            k = u * K + w
            st = udict.get(k)
            if st is None:
                st = [0, 0]
                udict[k] = st
            st.append(t)
            over = len(st) - 2 - self.u_keep[w]
            if over > 0:
                del st[2:2 + over]
            nl = len(st) - 2
            ub = 0
            for lim, win in pack.user_lims[w]:
                if nl >= lim:
                    x = st[2 + nl - lim] + win
                    if x > ub:
                        ub = x
            st[0] = ub
            st[1] = t + pack.min_interval[w] if pack.min_interval[w] > 0 else 0
        return w
