#!/usr/bin/env python3
"""Check: Seller gives exactly the same impressions as run_algorithm(best_price) from log_benchmark."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stand  # noqa: F401  (sets sys.path)
from stream import load_prepared, iter_days, nominal_requests
from ads import load_ads_file, build_pack
from engine_full import build_match_lists, run_algorithm
from seller import Seller

prep = load_prepared(stand.PREPARED)
ads = load_ads_file(os.path.join(HERE, "..", "log_benchmark", "ads_manual.json"))
sample = 0.01
nom = nominal_requests(prep, 1, sample)
pack = build_pack(prep, ads, nom, 1)
match = build_match_lists(prep, pack.targets)
ref = run_algorithm("best_price", pack, match, iter_days(prep, 1, sample), prep, seed=0, n_requests_hint=nom)
s = Seller(pack, match)
for _, ts, user, combo in iter_days(prep, 1, sample):
    for t, u, c in zip(ts.tolist(), user.tolist(), combo.tolist()):
        s.serve(t, u, c)
print("requests", nom, "ref imps", ref.total_impressions, "seller imps", s.total_impressions)
assert ref.impressions == s.impressions, "Minus: divergence"
assert abs(ref.revenue - s.revenue) < 1e-6
print("OK: Seller == run_algorithm(best_price)")
