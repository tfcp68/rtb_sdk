# Fixed-scenario strategy validation

Conditional descriptive results; bid seeds are not independent traffic periods.

| Strategy | Total | Random mean | Strategy delta vs frozen shading | Delta vs random min/max | p05 | p50 | p95 | Strictly beaten | Ties | Exceeds p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| full: SM (KM global) | 1.523e+07 | 1.458e+07 | 2.559e+05 | 6.483e+05/6.725e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| full: NM (wins-only global) | 1.523e+07 | 1.458e+07 | 2.559e+05 | 6.483e+05/6.725e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| full: NTM (tree, wins-only) | 1.517e+07 | 1.458e+07 | 1.949e+05 | 5.873e+05/6.115e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| full: STM (tree, KM) | 1.517e+07 | 1.458e+07 | 1.949e+05 | 5.873e+05/6.115e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| full: STM pruned (validation) | 1.516e+07 | 1.458e+07 | 1.861e+05 | 5.785e+05/6.027e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| full: Cui lognormal mixture | 1.469e+07 | 1.458e+07 | -2.846e+05 | 1.079e+05/1.32e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| full: Cui point-mean | 1.447e+07 | 1.458e+07 | -5.097e+05 | -1.173e+05/-9.308e+04 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 0.000 | 0 | False |
| censored: SM (KM global) | 1.523e+07 | 1.458e+07 | 2.559e+05 | 6.483e+05/6.725e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| censored: NM (wins-only global) | 1.524e+07 | 1.458e+07 | 2.621e+05 | 6.546e+05/6.787e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| censored: NTM (tree, wins-only) | 1.521e+07 | 1.458e+07 | 2.323e+05 | 6.248e+05/6.489e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| censored: STM (tree, KM) | 1.517e+07 | 1.458e+07 | 1.922e+05 | 5.846e+05/6.088e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| censored: STM pruned (validation) | 1.518e+07 | 1.458e+07 | 1.978e+05 | 5.902e+05/6.144e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| censored: Cui lognormal mixture | 1.483e+07 | 1.458e+07 | -1.482e+05 | 2.442e+05/2.684e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| censored: Cui point-mean | 1.471e+07 | 1.458e+07 | -2.683e+05 | 1.242e+05/1.483e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| baseline: shade alpha*v | 1.498e+07 | 1.458e+07 | 0 | 3.924e+05/4.166e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 1.000 | 0 | True |
| baseline: truthful b=v | 1.38e+07 | 1.458e+07 | -1.174e+06 | -7.811e+05/-7.569e+05 | 1.457e+07 | 1.458e+07 | 1.458e+07 | 0.000 | 0 | False |
