# Fixed-scenario strategy validation

Conditional descriptive results; bid seeds are not independent traffic periods.

| Strategy | Total | Random mean | Strategy delta vs frozen shading | Delta vs random min/max | p05 | p50 | p95 | Strictly beaten | Ties | Exceeds p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| full: SM (KM global) | 1.507e+07 | 1.442e+07 | 2.626e+05 | 6.396e+05/6.661e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| full: NM (wins-only global) | 1.507e+07 | 1.442e+07 | 2.626e+05 | 6.396e+05/6.661e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| full: NTM (tree, wins-only) | 1.501e+07 | 1.442e+07 | 2.002e+05 | 5.771e+05/6.037e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| full: STM (tree, KM) | 1.501e+07 | 1.442e+07 | 2.002e+05 | 5.771e+05/6.037e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| full: STM pruned (validation) | 1.5e+07 | 1.442e+07 | 1.938e+05 | 5.708e+05/5.973e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| full: Cui lognormal mixture | 1.453e+07 | 1.442e+07 | -2.757e+05 | 1.012e+05/1.278e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| full: Cui point-mean | 1.431e+07 | 1.442e+07 | -5.027e+05 | -1.257e+05/-9.922e+04 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 0.000 | 0 | False |
| censored: SM (KM global) | 1.507e+07 | 1.442e+07 | 2.626e+05 | 6.396e+05/6.661e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| censored: NM (wins-only global) | 1.508e+07 | 1.442e+07 | 2.691e+05 | 6.461e+05/6.726e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| censored: NTM (tree, wins-only) | 1.504e+07 | 1.442e+07 | 2.29e+05 | 6.06e+05/6.325e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| censored: STM (tree, KM) | 1.501e+07 | 1.442e+07 | 1.997e+05 | 5.766e+05/6.031e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| censored: STM pruned (validation) | 1.502e+07 | 1.442e+07 | 2.094e+05 | 5.863e+05/6.128e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| censored: Cui lognormal mixture | 1.467e+07 | 1.442e+07 | -1.386e+05 | 2.383e+05/2.649e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| censored: Cui point-mean | 1.455e+07 | 1.442e+07 | -2.638e+05 | 1.131e+05/1.397e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| baseline: shade alpha*v | 1.481e+07 | 1.442e+07 | 0 | 3.769e+05/4.035e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 1.000 | 0 | True |
| baseline: truthful b=v | 1.359e+07 | 1.442e+07 | -1.217e+06 | -8.396e+05/-8.131e+05 | 1.442e+07 | 1.442e+07 | 1.443e+07 | 0.000 | 0 | False |
