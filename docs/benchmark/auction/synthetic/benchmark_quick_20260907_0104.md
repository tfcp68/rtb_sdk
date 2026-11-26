# Comparative benchmark of auction algorithms

_Generated: 2026-09-07 01:04_

## Launch parameters

- Total scripts: 24
- A2/A3 runs by number of requests:
  - 10 k queries → 1000 runs
  - 100 k queries → 300 runs

## Assumption and simplification

- Filtration: Only precise match for specified vocab-limitations.
- User frequency limits (user_frequency_limit) and min_interval do not apply.
- For classic velocity/heuristics strategies, the monthly counter = the total number of impressions for the entire run (the entire run is considered one “month”).
- Volume-limitation for classic strategies is applied at the level of the benchmark engine, not through SDK filters.
- Classic strategies are implemented directly (without calling `auction()` from the SDK) for performance; the logic is identical to SDK implementation.
- For A2 and A3, the query stream is the same across all N runs; only the random initialization of `pj = exp(wj - 1)` prices changes.
- Budget for A3 = Volume × CPM announcements (monetary equivalent volume).

---

## Summary table

| №  | Campaigns | Requests | Traffic   | best_price impressions | A2 impressions (Wed.) | A3 impressions (Wed.) | best_price revenue | A2 revenue (Wed.) | A3 revenue (Wed.) |
| -- | -------- | -------- | -------- | ----------------- | --------------- | --------------- | ------------------ | ---------------- | ---------------- |
| 1  | 3        | 10k      | balanced | 8 819             | 8 826           | 8 825           | 1 915 280          | 1 778 179        | 1 773 089        |
| 2  | 3        | 10k      | shortage | 4 746             | 4 746           | 4 746           | 887 260            | 887 260          | 887 260          |
| 3  | 3        | 10k      | excess   | 8 909             | 8 909           | 8 909           | 2 151 560          | 1 919 233        | 1 919 989        |
| 4  | 3        | 100k     | balanced | 88 633            | 88 676          | 88 701          | 19 224 640         | 17 871 718       | 17 705 048       |
| 5  | 3        | 100k     | shortage | 47 484            | 47 484          | 47 484          | 8 877 260          | 8 877 260        | 8 877 260        |
| 6  | 3        | 100k     | excess   | 89 493            | 89 493          | 89 493          | 21 520 080         | 19 349 141       | 19 172 447       |
| 7  | 10       | 10k      | balanced | 9 970             | 9 969           | 9 968           | 2 535 120          | 2 237 945        | 2 246 237        |
| 8  | 10       | 10k      | shortage | 9 587             | 9 625           | 9 629           | 1 934 610          | 1 869 623        | 1 872 762        |
| 9  | 10       | 10k      | excess   | 9 970             | 9 970           | 9 970           | 2 585 840          | 2 317 393        | 2 320 337        |
| 10 | 10       | 100k     | balanced | 99 662            | 99 650          | 99 647          | 25 297 440         | 22 406 585       | 22 354 634       |
| 11 | 10       | 100k     | shortage | 96 003            | 96 357          | 96 203          | 19 366 950         | 18 710 748       | 18 635 476       |
| 12 | 10       | 100k     | excess   | 99 662            | 99 662          | 99 662          | 25 779 600         | 23 102 160       | 23 060 005       |
| 13 | 20       | 10k      | balanced | 10 000            | 9 999           | 9 999           | 2 539 210          | 2 230 498        | 2 237 806        |
| 14 | 20       | 10k      | shortage | 10 000            | 9 914           | 9 918           | 2 106 150          | 1 894 838        | 1 900 164        |
| 15 | 20       | 10k      | excess   | 10 000            | 10 000          | 10 000          | 2 589 930          | 2 298 142        | 2 301 945        |
| 16 | 20       | 100k     | balanced | 100 000           | 99 997          | 99 999          | 25 341 970         | 22 305 764       | 22 176 215       |
| 17 | 20       | 100k     | shortage | 100 000           | 99 200          | 99 265          | 21 058 950         | 19 065 307       | 18 947 721       |
| 18 | 20       | 100k     | excess   | 100 000           | 100 000         | 100 000         | 25 824 130         | 22 982 537       | 22 765 816       |
| 19 | 100      | 10k      | balanced | 10 000            | 10 000          | 10 000          | 2 655 572          | 2 336 979        | 2 332 530        |
| 20 | 100      | 10k      | shortage | 10 000            | 9 999           | 9 999           | 2 275 807          | 1 988 399        | 1 986 397        |
| 21 | 100      | 10k      | excess   | 10 000            | 10 000          | 10 000          | 2 698 508          | 2 385 776        | 2 380 161        |
| 22 | 100      | 100k     | balanced | 100 000           | 100 000         | 100 000         | 26 504 875         | 23 322 142       | 23 349 433       |
| 23 | 100      | 100k     | shortage | 100 000           | 99 998          | 99 998          | 22 763 618         | 19 923 669       | 19 922 550       |
| 24 | 100      | 100k     | excess   | 100 000           | 100 000         | 100 000         | 26 910 809         | 23 794 482       | 23 790 890       |

---

## 1 Scenario: Company 3, 10K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 3 |
| Requests | 10 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 15 107 impressions |
| Total budget (A3) | 2 824 280 units. |
| Mean CPM | 193.3 |

#### Participating companies

| Campaign     | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ------------ | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 4 202       | 1 176 560   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 6 051       | 968 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 4 854       | 679 560     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 8 819  | 88.2%     | 11.8%     | 1 915 280 | 217.2        |
| random_one        | 8 909  | 89.1%     | 10.9%     | 1 658 980 | 186.2        |
| best_price        | 8 819  | 88.2%     | 11.8%     | 1 915 280 | 217.2        |
| random_price      | 8 909  | 89.1%     | 10.9%     | 1 768 320 | 198.5        |
| best_velocity     | 8 909  | 89.1%     | 10.9%     | 1 665 560 | 187.0        |
| random_velocity   | 8 909  | 89.1%     | 10.9%     | 1 660 040 | 186.3        |
| best_heuristics   | 8 909  | 89.1%     | 10.9%     | 1 787 680 | 200.7        |
| random_heuristics | 8 909  | 89.1%     | 10.9%     | 1 770 560 | 198.7        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 8 798     | 8 909     | 8 819     | 8 827     |
| Fill rate | 88.0%     | 89.1%     | 88.2%     | 88.3%     |
| Revenue   | 1 363 520 | 1 915 280 | 1 838 380 | 1 778 179 |

> Distribution of impressions: 111 (1.3% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 8 798     | 8 909     | 8 819     | 8 826     |
| Fill rate | 88.0%     | 89.1%     | 88.2%     | 88.3%     |
| Revenue   | 1 363 520 | 1 915 280 | 1 838 380 | 1 773 089 |

> Distribution of impressions: 111 (1.3% from average)

#### Advertising displays (impressions (disposal volume))

| Ad   | Volume | best_one     | random_one  | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ------------ | ------ | ------------ | ----------- | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 4 202  | 4 202 (100%) | 2 413 (57%) | 4 202 (100%) | 3 224 (77%)  | 2 478 (59%)   | 2 413 (57%)     | 3 370 (80%)     | 3 240 (77%)       | 3 395 (81%)            | 3 334 (79%)    |
| Telecom_d46ed517452394a2 | 6 051  | 4 617 (76%)  | 3 695 (61%) | 4 617 (76%)  | 3 485 (58%)  | 3 569 (59%)   | 3 748 (62%)     | 3 431 (57%)     | 3 485 (58%)       | 3 353 (55%)            | 3 533 (58%)    |
| Retail_59c52779836b2bae | 4 854  | 0 (0%)       | 2 801 (58%) | 0 (0%)       | 2 200 (45%)  | 2 862 (59%)   | 2 748 (57%)     | 2 108 (43%)     | 2 184 (45%)       | 2 077 (43%)            | 1 958 (40%)    |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.1%, revenue -7.2%
- **A3 vs best_price**: impressions +0.1%, revenue -7.4%
- **A2 stability**: high (1.3% scatter)
- **A3 stability**: high (1.3% scatter)

---
## 2 Scenario: Company 3, 10K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 3 |
| Requests | 10 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 4 746 impressions |
| Total budget (A3) | 887 260 units. |
| Mean CPM | 193.3 |

#### Participating companies

| Campaign     | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ------------ | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 1 320       | 369 600     |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 1 901       | 304 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 1 525       | 213 500     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | ------- | ------------ |
| best_one          | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |
| random_one        | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |
| best_price        | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |
| random_price      | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |
| best_velocity     | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |
| random_velocity   | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |
| best_heuristics   | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |
| random_heuristics | 4 746  | 47.5%     | 52.5%     | 887 260 | 186.9        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min     | Max     | Median | Mean |
| --------- | ------- | ------- | ------- | ------- |
| Impressions    | 4 746   | 4 746   | 4 746   | 4 746   |
| Fill rate | 47.5%   | 47.5%   | 47.5%   | 47.5%   |
| Revenue   | 887 260 | 887 260 | 887 260 | 887 260 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min     | Max     | Median | Mean |
| --------- | ------- | ------- | ------- | ------- |
| Impressions    | 4 746   | 4 746   | 4 746   | 4 746   |
| Fill rate | 47.5%   | 47.5%   | 47.5%   | 47.5%   |
| Revenue   | 887 260 | 887 260 | 887 260 | 887 260 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad   | Volume | best_one     | random_one   | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ------------ | ------ | ------------ | ------------ | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 1 320  | 1 320 (100%) | 1 320 (100%) | 1 320 (100%) | 1 320 (100%) | 1 320 (100%)  | 1 320 (100%)    | 1 320 (100%)    | 1 320 (100%)      | 1 320 (100%)           | 1 320 (100%)   |
| Telecom_d46ed517452394a2 | 1 901  | 1 901 (100%) | 1 901 (100%) | 1 901 (100%) | 1 901 (100%) | 1 901 (100%)  | 1 901 (100%)    | 1 901 (100%)    | 1 901 (100%)      | 1 901 (100%)           | 1 901 (100%)   |
| Retail_59c52779836b2bae | 1 525  | 1 525 (100%) | 1 525 (100%) | 1 525 (100%) | 1 525 (100%) | 1 525 (100%)  | 1 525 (100%)    | 1 525 (100%)    | 1 525 (100%)      | 1 525 (100%)           | 1 525 (100%)   |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue +0.0%
- **A3 vs best_price**: impressions +0.0%, revenue +0.0%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 3 Scenario : Company 3, 10K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 3 |
| Requests | 10 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 64 752 impressions |
| Total budget (A3) | 12 105 660 units. |
| Mean CPM | 193.3 |

#### Participating companies

| Campaign     | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ------------ | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 18 012      | 5 043 360   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 25 935      | 4 149 600   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 20 805      | 2 912 700   |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 8 909  | 89.1%     | 10.9%     | 2 151 560 | 241.5        |
| random_one        | 8 909  | 89.1%     | 10.9%     | 1 658 980 | 186.2        |
| best_price        | 8 909  | 89.1%     | 10.9%     | 2 151 560 | 241.5        |
| random_price      | 8 909  | 89.1%     | 10.9%     | 1 768 320 | 198.5        |
| best_velocity     | 8 909  | 89.1%     | 10.9%     | 1 665 560 | 187.0        |
| random_velocity   | 8 909  | 89.1%     | 10.9%     | 1 659 140 | 186.2        |
| best_heuristics   | 8 909  | 89.1%     | 10.9%     | 2 151 560 | 241.5        |
| random_heuristics | 8 909  | 89.1%     | 10.9%     | 1 814 560 | 203.7        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 8 909     | 8 909     | 8 909     | 8 909     |
| Fill rate | 89.1%     | 89.1%     | 89.1%     | 89.1%     |
| Revenue   | 1 322 000 | 2 151 560 | 2 101 360 | 1 919 233 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 8 909     | 8 909     | 8 909     | 8 909     |
| Fill rate | 89.1%     | 89.1%     | 89.1%     | 89.1%     |
| Revenue   | 1 322 000 | 2 151 560 | 2 101 360 | 1 919 989 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad   | Volume | best_one    | random_one  | best_price  | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ------------ | ------ | ----------- | ----------- | ----------- | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 18 012 | 6 051 (34%) | 2 413 (13%) | 6 051 (34%) | 3 224 (18%)  | 2 478 (14%)   | 2 395 (13%)     | 6 051 (34%)     | 3 573 (20%)       | 4 393 (24%)            | 4 380 (24%)    |
| Telecom_d46ed517452394a2 | 25 935 | 2 858 (11%) | 3 695 (14%) | 2 858 (11%) | 3 485 (13%)  | 3 569 (14%)   | 3 829 (15%)     | 2 858 (11%)     | 3 354 (13%)       | 2 841 (11%)            | 2 974 (11%)    |
| Retail_59c52779836b2bae | 20 805 | 0 (0%)      | 2 801 (13%) | 0 (0%)      | 2 200 (11%)  | 2 862 (14%)   | 2 685 (13%)     | 0 (0%)          | 1 982 (10%)       | 1 673 (8%)             | 1 554 (7%)     |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -10.8%
- **A3 vs best_price**: impressions +0.0%, revenue -10.8%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
## 4 Scenario: Company 3, 100K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 3 |
| Requests | 100 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 151 087 impressions |
| Total budget (A3) | 28 246 380 units. |
| Mean CPM | 193.3 |

#### Participating companies

| Campaign     | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ------------ | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 42 028      | 11 767 840  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 60 514      | 9 682 240   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 48 545      | 6 796 300   |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | ---------- | ------------ |
| best_one          | 88 633 | 88.6%     | 11.4%     | 19 224 640 | 216.9        |
| random_one        | 89 493 | 89.5%     | 10.5%     | 16 703 660 | 186.6        |
| best_price        | 88 633 | 88.6%     | 11.4%     | 19 224 640 | 216.9        |
| random_price      | 89 493 | 89.5%     | 10.5%     | 17 762 080 | 198.5        |
| best_velocity     | 89 493 | 89.5%     | 10.5%     | 16 731 060 | 187.0        |
| random_velocity   | 89 493 | 89.5%     | 10.5%     | 16 694 240 | 186.5        |
| best_heuristics   | 89 493 | 89.5%     | 10.5%     | 17 944 880 | 200.5        |
| random_heuristics | 89 493 | 89.5%     | 10.5%     | 17 765 360 | 198.5        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 88 402     | 89 493     | 88 633     | 88 677     |
| Fill rate | 88.4%      | 89.5%      | 88.6%      | 88.7%      |
| Revenue   | 13 703 300 | 19 224 640 | 18 445 460 | 17 871 718 |

> Distribution of impressions: 1 091 (1.2% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 88 402     | 89 493     | 88 633     | 88 701     |
| Fill rate | 88.4%      | 89.5%      | 88.6%      | 88.7%      |
| Revenue   | 13 703 300 | 19 224 640 | 18 445 460 | 17 705 048 |

> Distribution of impressions: 1 091 (1.2% from average)

#### Advertising displays (impressions (disposal volume))

| Ad   | Volume | best_one      | random_one   | best_price    | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ------------ | ------ | ------------- | ------------ | ------------- | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 42 028 | 42 028 (100%) | 24 403 (58%) | 42 028 (100%) | 32 459 (77%) | 24 894 (59%)  | 24 448 (58%)    | 33 760 (80%)    | 32 433 (77%)      | 34 211 (81%)           | 32 788 (78%)   |
| Telecom_d46ed517452394a2 | 60 514 | 46 605 (77%)  | 37 911 (63%) | 46 605 (77%)  | 34 440 (57%) | 35 844 (59%)  | 37 125 (61%)    | 34 473 (57%)    | 34 786 (57%)      | 33 367 (55%)           | 34 828 (58%)   |
| Retail_59c52779836b2bae | 48 545 | 0 (0%)        | 27 179 (56%) | 0 (0%)        | 22 594 (47%) | 28 755 (59%)  | 27 920 (58%)    | 21 260 (44%)    | 22 274 (46%)      | 21 097 (43%)           | 21 084 (43%)   |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -7.0%
- **A3 vs best_price**: impressions +0.1%, revenue -7.9%
- **A2 stability**: high (1.2% scatter)
- **A3 stability**: high (1.2% scatter)

---
## 5 Scenario: Company 3, 100K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 3 |
| Requests | 100 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 47 484 impressions |
| Total budget (A3) | 8 877 260 units. |
| Mean CPM | 193.3 |

#### Participating companies

| Campaign     | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ------------ | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 13 208      | 3 698 240   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 19 019      | 3 043 040   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 15 257      | 2 135 980   |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |
| random_one        | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |
| best_price        | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |
| random_price      | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |
| best_velocity     | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |
| random_velocity   | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |
| best_heuristics   | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |
| random_heuristics | 47 484 | 47.5%     | 52.5%     | 8 877 260 | 187.0        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 47 484    | 47 484    | 47 484    | 47 484    |
| Fill rate | 47.5%     | 47.5%     | 47.5%     | 47.5%     |
| Revenue   | 8 877 260 | 8 877 260 | 8 877 260 | 8 877 260 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 47 484    | 47 484    | 47 484    | 47 484    |
| Fill rate | 47.5%     | 47.5%     | 47.5%     | 47.5%     |
| Revenue   | 8 877 260 | 8 877 260 | 8 877 260 | 8 877 260 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad   | Volume | best_one      | random_one    | best_price    | random_price  | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ------------ | ------ | ------------- | ------------- | ------------- | ------------- | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 13 208 | 13 208 (100%) | 13 208 (100%) | 13 208 (100%) | 13 208 (100%) | 13 208 (100%) | 13 208 (100%)   | 13 208 (100%)   | 13 208 (100%)     | 13 208 (100%)          | 13 208 (100%)  |
| Telecom_d46ed517452394a2 | 19 019 | 19 019 (100%) | 19 019 (100%) | 19 019 (100%) | 19 019 (100%) | 19 019 (100%) | 19 019 (100%)   | 19 019 (100%)   | 19 019 (100%)     | 19 019 (100%)          | 19 019 (100%)  |
| Retail_59c52779836b2bae | 15 257 | 15 257 (100%) | 15 257 (100%) | 15 257 (100%) | 15 257 (100%) | 15 257 (100%) | 15 257 (100%)   | 15 257 (100%)   | 15 257 (100%)     | 15 257 (100%)          | 15 257 (100%)  |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue +0.0%
- **A3 vs best_price**: impressions +0.0%, revenue +0.0%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 6 Scenario : Company 3, 100K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 3 |
| Requests | 100 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 647 520 impressions |
| Total budget (A3) | 121 056 600 units. |
| Mean CPM | 193.3 |

#### Participating companies

| Campaign     | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ------------ | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 180 120     | 50 433 600  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 259 350     | 41 496 000  |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 208 050     | 29 127 000  |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | ---------- | ------------ |
| best_one          | 89 493 | 89.5%     | 10.5%     | 21 520 080 | 240.5        |
| random_one        | 89 493 | 89.5%     | 10.5%     | 16 703 660 | 186.6        |
| best_price        | 89 493 | 89.5%     | 10.5%     | 21 520 080 | 240.5        |
| random_price      | 89 493 | 89.5%     | 10.5%     | 17 762 080 | 198.5        |
| best_velocity     | 89 493 | 89.5%     | 10.5%     | 16 731 080 | 187.0        |
| random_velocity   | 89 493 | 89.5%     | 10.5%     | 16 677 000 | 186.3        |
| best_heuristics   | 89 493 | 89.5%     | 10.5%     | 21 520 080 | 240.5        |
| random_heuristics | 89 493 | 89.5%     | 10.5%     | 18 186 880 | 203.2        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 89 493     | 89 493     | 89 493     | 89 493     |
| Fill rate | 89.5%      | 89.5%      | 89.5%      | 89.5%      |
| Revenue   | 13 287 160 | 21 520 080 | 21 001 460 | 19 349 141 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 89 493     | 89 493     | 89 493     | 89 493     |
| Fill rate | 89.5%      | 89.5%      | 89.5%      | 89.5%      |
| Revenue   | 13 287 160 | 21 520 080 | 21 001 460 | 19 172 447 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad   | Volume  | best_one     | random_one   | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ------------ | ------- | ------------ | ------------ | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 180 120 | 60 010 (33%) | 24 403 (14%) | 60 010 (33%) | 32 459 (18%) | 24 894 (14%)  | 24 234 (13%)    | 60 010 (33%)    | 35 588 (20%)      | 44 572 (25%)           | 43 250 (24%)   |
| Telecom_d46ed517452394a2 | 259 350 | 29 483 (11%) | 37 911 (15%) | 29 483 (11%) | 34 440 (13%) | 35 845 (14%)  | 37 761 (15%)    | 29 483 (11%)    | 33 777 (13%)      | 28 995 (11%)           | 29 419 (11%)   |
| Retail_59c52779836b2bae | 208 050 | 0 (0%)       | 27 179 (13%) | 0 (0%)       | 22 594 (11%) | 28 754 (14%)  | 27 498 (13%)    | 0 (0%)          | 20 128 (10%)      | 15 924 (8%)            | 16 823 (8%)    |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -10.1%
- **A3 vs best_price**: impressions +0.0%, revenue -10.9%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
## 7 Scenario: Company 10, 10K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 10 |
| Requests | 10 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 34 534 impressions |
| Total budget (A3) | 6 612 020 units. |
| Mean CPM | 192.0 |

#### Participating companies

| Campaign        | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| --------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 4 202       | 1 176 560   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 6 051       | 968 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 4 854       | 679 560     |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 1 741       | 156 690     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 2 553       | 638 250     |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 4 700       | 940 000     |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 2 872       | 919 040     |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 2 657       | 345 410     |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 3 849       | 577 350     |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 1 055       | 211 000     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 9 970  | 99.7%     | 0.3%      | 2 132 380 | 213.9        |
| random_one        | 9 970  | 99.7%     | 0.3%      | 1 843 290 | 184.9        |
| best_price        | 9 970  | 99.7%     | 0.3%      | 2 535 120 | 254.3        |
| random_price      | 9 970  | 99.7%     | 0.3%      | 1 989 900 | 199.6        |
| best_velocity     | 9 970  | 99.7%     | 0.3%      | 1 908 860 | 191.5        |
| random_velocity   | 9 970  | 99.7%     | 0.3%      | 1 858 450 | 186.4        |
| best_heuristics   | 9 970  | 99.7%     | 0.3%      | 2 389 370 | 239.7        |
| random_heuristics | 9 970  | 99.7%     | 0.3%      | 2 025 700 | 203.2        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 933     | 9 970     | 9 970     | 9 969     |
| Fill rate | 99.3%     | 99.7%     | 99.7%     | 99.7%     |
| Revenue   | 1 474 830 | 2 535 120 | 2 270 025 | 2 237 945 |

> Distribution of impressions: 37 (0.4% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 903     | 9 970     | 9 970     | 9 969     |
| Fill rate | 99.0%     | 99.7%     | 99.7%     | 99.7%     |
| Revenue   | 1 481 110 | 2 534 820 | 2 274 335 | 2 246 237 |

> Distribution of impressions: 67 (0.7% from average)

#### Advertising displays (impressions (disposal volume))

| Ad      | Volume | best_one     | random_one  | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| --------------- | ------ | ------------ | ----------- | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 4 202  | 4 202 (100%) | 974 (23%)   | 3 179 (76%)  | 1 383 (33%)  | 1 213 (29%)   | 1 040 (25%)     | 2 625 (62%)     | 1 570 (37%)       | 2 201 (52%)            | 2 230 (53%)    |
| Telecom_d46ed517452394a2 | 6 051  | 4 617 (76%)  | 1 809 (30%) | 1 986 (33%)  | 1 675 (28%)  | 1 747 (29%)   | 1 804 (30%)     | 1 632 (27%)     | 1 743 (29%)       | 1 481 (24%)            | 1 326 (22%)    |
| Retail_59c52779836b2bae | 4 854  | 0 (0%)       | 1 449 (30%) | 0 (0%)       | 1 214 (25%)  | 1 402 (29%)   | 1 412 (29%)     | 223 (5%)        | 1 142 (24%)       | 709 (15%)              | 809 (17%)      |
| Campaign_51288482374d537c | 1 741  | 0 (0%)       | 482 (28%)   | 0 (0%)       | 298 (17%)    | 502 (29%)     | 492 (28%)       | 0 (0%)          | 262 (15%)         | 57 (3%)                | 53 (3%)        |
| Automotive_9e1edff89ac9a790 | 2 553  | 77 (3%)      | 683 (27%)   | 758 (30%)    | 924 (36%)    | 737 (29%)     | 740 (29%)       | 1 360 (53%)     | 961 (38%)         | 1 134 (44%)            | 1 130 (44%)    |
| Campaign_4d4dc901c2e49788 | 4 700  | 767 (16%)    | 1 337 (28%) | 721 (15%)    | 1 417 (30%)  | 1 357 (29%)   | 1 379 (29%)     | 1 612 (34%)     | 1 395 (30%)       | 1 325 (28%)            | 1 361 (29%)    |
| Property_5a34d256a53751c3 | 2 872  | 0 (0%)       | 685 (24%)   | 2 872 (100%) | 974 (34%)    | 829 (29%)     | 674 (23%)       | 1 824 (64%)     | 1 002 (35%)       | 1 576 (55%)            | 1 604 (56%)    |
| Retail_5d131e8ff2fd6390 | 2 657  | 80 (3%)      | 848 (32%)   | 60 (2%)      | 635 (24%)    | 767 (29%)     | 784 (30%)       | 60 (2%)         | 559 (21%)         | 388 (15%)              | 367 (14%)      |
| Health_0676356d6ba137b6 | 3 849  | 227 (6%)     | 1 466 (38%) | 242 (6%)     | 1 215 (32%)  | 1 112 (29%)   | 1 415 (37%)     | 373 (10%)       | 1 120 (29%)       | 851 (22%)              | 836 (22%)      |
| Travel_3724963d1920e16a | 1 055  | 0 (0%)       | 237 (22%)   | 152 (14%)    | 235 (22%)    | 304 (29%)     | 230 (22%)       | 261 (25%)       | 216 (20%)         | 243 (23%)              | 249 (24%)      |


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.0%, revenue -11.7%
- **A3 vs best_price**: impressions -0.0%, revenue -11.4%
- **A2 stability**: high (0.4% scatter)
- **A3 stability**: high (0.7% scatter)

---
## 8 Scenario: Company 10, 10K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 10 |
| Requests | 10 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 10 850 impressions |
| Total budget (A3) | 2 077 280 units. |
| Mean CPM | 192.0 |

#### Participating companies

| Campaign        | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| --------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 1 320       | 369 600     |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 1 901       | 304 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 1 525       | 213 500     |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 547         | 49 230      |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 802         | 200 500     |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 1 477       | 295 400     |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 902         | 288 640     |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 835         | 108 550     |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 1 210       | 181 500     |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 331         | 66 200      |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 9 672  | 96.7%     | 3.3%      | 1 848 050 | 191.1        |
| random_one        | 9 934  | 99.3%     | 0.7%      | 1 853 750 | 186.6        |
| best_price        | 9 587  | 95.9%     | 4.1%      | 1 934 610 | 201.8        |
| random_price      | 9 956  | 99.6%     | 0.4%      | 1 957 720 | 196.6        |
| best_velocity     | 9 970  | 99.7%     | 0.3%      | 1 908 920 | 191.5        |
| random_velocity   | 9 970  | 99.7%     | 0.3%      | 1 891 250 | 189.7        |
| best_heuristics   | 9 970  | 99.7%     | 0.3%      | 1 932 630 | 193.8        |
| random_heuristics | 9 970  | 99.7%     | 0.3%      | 1 952 780 | 195.9        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 059     | 9 961     | 9 641     | 9 625     |
| Fill rate | 90.6%     | 99.6%     | 96.4%     | 96.3%     |
| Revenue   | 1 565 550 | 1 977 470 | 1 886 425 | 1 869 623 |

> Distribution of impressions: 902 (9.4% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 069     | 9 953     | 9 646     | 9 629     |
| Fill rate | 90.7%     | 99.5%     | 96.5%     | 96.3%     |
| Revenue   | 1 582 110 | 1 977 760 | 1 889 570 | 1 872 762 |

> Distribution of impressions: 884 (9.2% from average)

#### Advertising displays (impressions (disposal volume))

| Ad      | Volume | best_one     | random_one   | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| --------------- | ------ | ------------ | ------------ | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 1 320  | 1 320 (100%) | 986 (75%)    | 1 320 (100%) | 1 320 (100%) | 1 213 (92%)   | 1 157 (88%)     | 1 272 (96%)     | 1 305 (99%)       | 1 219 (92%)            | 1 220 (92%)    |
| Telecom_d46ed517452394a2 | 1 901  | 1 901 (100%) | 1 872 (98%)  | 1 901 (100%) | 1 769 (93%)  | 1 747 (92%)   | 1 775 (93%)     | 1 749 (92%)     | 1 785 (94%)       | 1 745 (92%)            | 1 748 (92%)    |
| Retail_59c52779836b2bae | 1 525  | 1 525 (100%) | 1 442 (95%)  | 1 525 (100%) | 1 260 (83%)  | 1 401 (92%)   | 1 404 (92%)     | 1 365 (90%)     | 1 318 (86%)       | 1 306 (86%)            | 1 348 (88%)    |
| Campaign_51288482374d537c | 547    | 547 (100%)   | 469 (86%)    | 9 (2%)       | 320 (59%)    | 502 (92%)     | 500 (91%)       | 442 (81%)       | 350 (64%)         | 321 (59%)              | 302 (55%)      |
| Automotive_9e1edff89ac9a790 | 802    | 802 (100%)   | 725 (90%)    | 802 (100%)   | 802 (100%)   | 737 (92%)     | 736 (92%)       | 766 (96%)       | 795 (99%)         | 720 (90%)              | 724 (90%)      |
| Campaign_4d4dc901c2e49788 | 1 477  | 1 477 (100%) | 1 453 (98%)  | 1 477 (100%) | 1 477 (100%) | 1 358 (92%)   | 1 385 (94%)     | 1 382 (94%)     | 1 424 (96%)       | 1 377 (93%)            | 1 376 (93%)    |
| Property_5a34d256a53751c3 | 902    | 665 (74%)    | 698 (77%)    | 902 (100%)   | 902 (100%)   | 829 (92%)     | 768 (85%)       | 870 (96%)       | 897 (99%)         | 832 (92%)              | 836 (93%)      |
| Retail_5d131e8ff2fd6390 | 835    | 697 (83%)    | 835 (100%)   | 110 (13%)    | 648 (78%)    | 767 (92%)     | 774 (93%)       | 725 (87%)       | 659 (79%)         | 679 (81%)              | 660 (79%)      |
| Health_0676356d6ba137b6 | 1 210  | 707 (58%)    | 1 210 (100%) | 1 210 (100%) | 1 210 (100%) | 1 112 (92%)   | 1 197 (99%)     | 1 092 (90%)     | 1 158 (96%)       | 1 154 (95%)            | 1 138 (94%)    |
| Travel_3724963d1920e16a | 331    | 31 (9%)      | 244 (74%)    | 331 (100%)   | 248 (75%)    | 304 (92%)     | 274 (83%)       | 307 (93%)       | 279 (84%)         | 266 (80%)              | 272 (82%)      |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.4%, revenue -3.4%
- **A3 vs best_price**: impressions +0.4%, revenue -3.2%
- **A2 stability**: moderate (spread 9.4%)
- **A3 stability**: moderate (spread 9.2%)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 9 Scenario : Company 10, 10K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 10 |
| Requests | 10 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 148 030 impressions |
| Total budget (A3) | 28 342 590 units. |
| Mean CPM | 192.0 |

#### Participating companies

| Campaign        | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| --------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 18 012      | 5 043 360   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 25 935      | 4 149 600   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 20 805      | 2 912 700   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 7 465       | 671 850     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 10 944      | 2 736 000   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 20 145      | 4 029 000   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 12 312      | 3 939 840   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 11 388      | 1 480 440   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 16 500      | 2 475 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 4 524       | 904 800     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 9 970  | 99.7%     | 0.3%      | 2 348 460 | 235.6        |
| random_one        | 9 970  | 99.7%     | 0.3%      | 1 843 290 | 184.9        |
| best_price        | 9 970  | 99.7%     | 0.3%      | 2 585 840 | 259.4        |
| random_price      | 9 970  | 99.7%     | 0.3%      | 1 989 900 | 199.6        |
| best_velocity     | 9 970  | 99.7%     | 0.3%      | 1 908 980 | 191.5        |
| random_velocity   | 9 970  | 99.7%     | 0.3%      | 1 850 840 | 185.6        |
| best_heuristics   | 9 970  | 99.7%     | 0.3%      | 2 525 080 | 253.3        |
| random_heuristics | 9 970  | 99.7%     | 0.3%      | 2 036 890 | 204.3        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 970     | 9 970     | 9 970     | 9 970     |
| Fill rate | 99.7%     | 99.7%     | 99.7%     | 99.7%     |
| Revenue   | 1 434 200 | 2 585 840 | 2 358 080 | 2 317 393 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 970     | 9 970     | 9 970     | 9 970     |
| Fill rate | 99.7%     | 99.7%     | 99.7%     | 99.7%     |
| Revenue   | 1 443 740 | 2 585 540 | 2 359 500 | 2 320 337 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad      | Volume | best_one    | random_one | best_price  | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| --------------- | ------ | ----------- | ---------- | ----------- | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 18 012 | 6 051 (34%) | 974 (5%)   | 1 911 (11%) | 1 383 (8%)   | 1 213 (7%)    | 1 016 (6%)      | 3 430 (19%)     | 1 618 (9%)        | 2 446 (14%)            | 2 411 (13%)    |
| Telecom_d46ed517452394a2 | 25 935 | 2 858 (11%) | 1 809 (7%) | 1 986 (8%)  | 1 675 (6%)   | 1 747 (7%)    | 1 812 (7%)      | 1 986 (8%)      | 1 730 (7%)        | 1 317 (5%)             | 1 212 (5%)     |
| Retail_59c52779836b2bae | 20 805 | 0 (0%)      | 1 449 (7%) | 0 (0%)      | 1 214 (6%)   | 1 401 (7%)    | 1 414 (7%)      | 0 (0%)          | 1 130 (5%)        | 660 (3%)               | 758 (4%)       |
| Campaign_51288482374d537c | 7 465  | 0 (0%)      | 482 (6%)   | 0 (0%)      | 298 (4%)     | 503 (7%)      | 488 (7%)        | 0 (0%)          | 241 (3%)          | 54 (1%)                | 50 (1%)        |
| Automotive_9e1edff89ac9a790 | 10 944 | 33 (0%)     | 683 (6%)   | 758 (7%)    | 924 (8%)     | 737 (7%)      | 742 (7%)        | 758 (7%)        | 987 (9%)          | 1 107 (10%)            | 1 127 (10%)    |
| Campaign_4d4dc901c2e49788 | 20 145 | 721 (4%)    | 1 337 (7%) | 721 (4%)    | 1 417 (7%)   | 1 357 (7%)    | 1 371 (7%)      | 721 (4%)        | 1 385 (7%)        | 1 096 (5%)             | 1 098 (5%)     |
| Property_5a34d256a53751c3 | 12 312 | 0 (0%)      | 685 (6%)   | 4 140 (34%) | 974 (8%)     | 830 (7%)      | 651 (5%)        | 2 621 (21%)     | 1 012 (8%)        | 1 952 (16%)            | 1 990 (16%)    |
| Retail_5d131e8ff2fd6390 | 11 388 | 80 (1%)     | 848 (7%)   | 60 (1%)     | 635 (6%)     | 767 (7%)      | 793 (7%)        | 60 (1%)         | 544 (5%)          | 364 (3%)               | 344 (3%)       |
| Health_0676356d6ba137b6 | 16 500 | 227 (1%)    | 1 466 (9%) | 242 (1%)    | 1 215 (7%)   | 1 111 (7%)    | 1 463 (9%)      | 242 (1%)        | 1 115 (7%)        | 762 (5%)               | 763 (5%)       |
| Travel_3724963d1920e16a | 4 524  | 0 (0%)      | 237 (5%)   | 152 (3%)    | 235 (5%)     | 304 (7%)      | 220 (5%)        | 152 (3%)        | 208 (5%)          | 208 (5%)               | 212 (5%)       |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -10.4%
- **A3 vs best_price**: impressions +0.0%, revenue -10.3%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
## 10 Scenario: Company 10, 100K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 10 |
| Requests | 100 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 345 403 impressions |
| Total budget (A3) | 66 132 610 units. |
| Mean CPM | 192.0 |

#### Participating companies

| Campaign        | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| --------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 42 028      | 11 767 840  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 60 514      | 9 682 240   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 48 545      | 6 796 300   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 17 419      | 1 567 710   |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 25 536      | 6 384 000   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 47 005      | 9 401 000   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 28 728      | 9 192 960   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 26 572      | 3 454 360   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 38 500      | 5 775 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 10 556      | 2 111 200   |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | ---------- | ------------ |
| best_one          | 99 662 | 99.7%     | 0.3%      | 21 316 490 | 213.9        |
| random_one        | 99 662 | 99.7%     | 0.3%      | 18 391 890 | 184.5        |
| best_price        | 99 662 | 99.7%     | 0.3%      | 25 297 440 | 253.8        |
| random_price      | 99 662 | 99.7%     | 0.3%      | 19 770 290 | 198.4        |
| best_velocity     | 99 662 | 99.7%     | 0.3%      | 19 081 770 | 191.5        |
| random_velocity   | 99 662 | 99.7%     | 0.3%      | 18 466 400 | 185.3        |
| best_heuristics   | 99 662 | 99.7%     | 0.3%      | 23 849 010 | 239.3        |
| random_heuristics | 99 662 | 99.7%     | 0.3%      | 20 199 800 | 202.7        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 070     | 99 662     | 99 662     | 99 650     |
| Fill rate | 99.1%      | 99.7%      | 99.7%      | 99.7%      |
| Revenue   | 15 427 570 | 25 297 440 | 22 739 110 | 22 406 585 |

> Distribution of impressions: 592 (0.6% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 070     | 99 662     | 99 662     | 99 647     |
| Fill rate | 99.1%      | 99.7%      | 99.7%      | 99.6%      |
| Revenue   | 15 195 060 | 25 297 440 | 22 716 790 | 22 354 634 |

> Distribution of impressions: 592 (0.6% from average)

#### Advertising displays (impressions (disposal volume))

| Ad      | Volume | best_one      | random_one   | best_price    | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| --------------- | ------ | ------------- | ------------ | ------------- | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 42 028 | 42 028 (100%) | 10 015 (24%) | 31 282 (74%)  | 13 692 (33%) | 12 127 (29%)  | 10 199 (24%)    | 26 154 (62%)    | 15 678 (37%)      | 19 855 (47%)           | 21 068 (50%)   |
| Telecom_d46ed517452394a2 | 60 514 | 46 605 (77%)  | 18 632 (31%) | 20 605 (34%)  | 17 578 (29%) | 17 461 (29%)  | 18 594 (31%)    | 16 583 (27%)    | 18 063 (30%)      | 15 779 (26%)           | 15 643 (26%)   |
| Retail_59c52779836b2bae | 48 545 | 0 (0%)        | 14 376 (30%) | 0 (0%)        | 12 164 (25%) | 14 008 (29%)  | 14 297 (29%)    | 2 514 (5%)      | 11 396 (23%)      | 7 573 (16%)            | 7 336 (15%)    |
| Campaign_51288482374d537c | 17 419 | 0 (0%)        | 4 895 (28%)  | 0 (0%)        | 2 873 (16%)  | 5 026 (29%)   | 4 919 (28%)     | 0 (0%)          | 2 490 (14%)       | 542 (3%)               | 467 (3%)       |
| Automotive_9e1edff89ac9a790 | 25 536 | 756 (3%)      | 6 902 (27%)  | 7 673 (30%)   | 8 580 (34%)  | 7 368 (29%)   | 7 018 (27%)     | 13 534 (53%)    | 9 026 (35%)       | 11 912 (47%)           | 11 080 (43%)   |
| Campaign_4d4dc901c2e49788 | 47 005 | 7 526 (16%)   | 13 430 (29%) | 7 065 (15%)   | 13 869 (30%) | 13 562 (29%)  | 13 529 (29%)    | 15 934 (34%)    | 13 882 (30%)      | 13 033 (28%)           | 13 552 (29%)   |
| Property_5a34d256a53751c3 | 28 728 | 0 (0%)        | 6 321 (22%)  | 28 728 (100%) | 9 536 (33%)  | 8 289 (29%)   | 6 525 (23%)     | 18 179 (63%)    | 9 998 (35%)       | 17 126 (60%)           | 16 208 (56%)   |
| Retail_5d131e8ff2fd6390 | 26 572 | 720 (3%)      | 8 157 (31%)  | 534 (2%)      | 6 740 (25%)  | 7 667 (29%)   | 8 140 (31%)     | 534 (2%)        | 5 741 (22%)       | 3 201 (12%)            | 3 391 (13%)    |
| Health_0676356d6ba137b6 | 38 500 | 2 027 (5%)    | 14 561 (38%) | 2 139 (6%)    | 12 200 (32%) | 11 108 (29%)  | 14 067 (37%)    | 3 647 (9%)      | 11 117 (29%)      | 7 866 (20%)            | 8 092 (21%)    |
| Travel_3724963d1920e16a | 10 556 | 0 (0%)        | 2 373 (22%)  | 1 636 (15%)   | 2 430 (23%)  | 3 046 (29%)   | 2 374 (22%)     | 2 583 (24%)     | 2 271 (22%)       | 2 757 (26%)            | 2 806 (27%)    |


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.0%, revenue -11.4%
- **A3 vs best_price**: impressions -0.0%, revenue -11.6%
- **A2 stability**: high (0.6% scatter)
- **A3 stability**: high (0.6% scatter)

---
## 11 Scenario: Company 10, 100K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 10 |
| Requests | 100 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 108 552 impressions |
| Total budget (A3) | 20 783 760 units. |
| Mean CPM | 192.0 |

#### Participating companies

| Campaign        | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| --------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 13 208      | 3 698 240   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 19 019      | 3 043 040   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 15 257      | 2 135 980   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 5 474       | 492 660     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 8 025       | 2 006 250   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 14 773      | 2 954 600   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 9 028       | 2 888 960   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 8 351       | 1 085 630   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 12 100      | 1 815 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 3 317       | 663 400     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | ---------- | ------------ |
| best_one          | 96 692 | 96.7%     | 3.3%      | 18 572 100 | 192.1        |
| random_one        | 99 300 | 99.3%     | 0.7%      | 18 455 180 | 185.9        |
| best_price        | 96 003 | 96.0%     | 4.0%      | 19 366 950 | 201.7        |
| random_price      | 99 595 | 99.6%     | 0.4%      | 19 583 590 | 196.6        |
| best_velocity     | 99 662 | 99.7%     | 0.3%      | 19 081 520 | 191.5        |
| random_velocity   | 99 662 | 99.7%     | 0.3%      | 18 853 300 | 189.2        |
| best_heuristics   | 99 662 | 99.7%     | 0.3%      | 19 320 520 | 193.9        |
| random_heuristics | 99 662 | 99.7%     | 0.3%      | 19 491 800 | 195.6        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 91 942     | 99 468     | 96 489     | 96 358     |
| Fill rate | 91.9%      | 99.5%      | 96.5%      | 96.4%      |
| Revenue   | 16 284 260 | 19 765 380 | 18 891 500 | 18 710 748 |

> Distribution of impressions: 7 526 (7.8% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 91 286     | 99 457     | 96 400     | 96 203     |
| Fill rate | 91.3%      | 99.5%      | 96.4%      | 96.2%      |
| Revenue   | 15 795 320 | 19 751 890 | 18 831 575 | 18 635 476 |

> Distribution of impressions: 8 171 (8.5% from average)

#### Advertising displays (impressions (disposal volume))

| Ad      | Volume | best_one      | random_one    | best_price    | random_price  | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| --------------- | ------ | ------------- | ------------- | ------------- | ------------- | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 13 208 | 13 208 (100%) | 10 290 (78%)  | 13 208 (100%) | 13 208 (100%) | 12 126 (92%)  | 11 436 (87%)    | 12 719 (96%)    | 13 040 (99%)      | 12 186 (92%)           | 12 079 (91%)   |
| Telecom_d46ed517452394a2 | 19 019 | 19 019 (100%) | 19 019 (100%) | 19 019 (100%) | 18 102 (95%)  | 17 461 (92%)  | 17 888 (94%)    | 17 479 (92%)    | 17 878 (94%)      | 17 537 (92%)           | 17 603 (93%)   |
| Retail_59c52779836b2bae | 15 257 | 15 257 (100%) | 14 588 (96%)  | 15 257 (100%) | 12 435 (82%)  | 14 008 (92%)  | 14 217 (93%)    | 13 644 (89%)    | 13 128 (86%)      | 13 464 (88%)           | 13 271 (87%)   |
| Campaign_51288482374d537c | 5 474  | 5 474 (100%)  | 4 850 (89%)   | 110 (2%)      | 2 922 (53%)   | 5 026 (92%)   | 5 003 (91%)     | 4 424 (81%)     | 3 568 (65%)       | 3 368 (62%)            | 3 254 (59%)    |
| Automotive_9e1edff89ac9a790 | 8 025  | 8 025 (100%)  | 7 101 (88%)   | 8 025 (100%)  | 8 025 (100%)  | 7 368 (92%)   | 7 263 (91%)     | 7 656 (95%)     | 7 905 (99%)       | 7 547 (94%)            | 7 304 (91%)    |
| Campaign_4d4dc901c2e49788 | 14 773 | 14 773 (100%) | 14 127 (96%)  | 14 773 (100%) | 14 404 (98%)  | 13 563 (92%)  | 13 768 (93%)    | 13 816 (94%)    | 14 164 (96%)      | 13 306 (90%)           | 13 671 (93%)   |
| Property_5a34d256a53751c3 | 9 028  | 7 160 (79%)   | 6 467 (72%)   | 9 028 (100%)  | 9 028 (100%)  | 8 288 (92%)   | 7 562 (84%)     | 8 704 (96%)     | 8 885 (98%)       | 8 271 (92%)            | 8 020 (89%)    |
| Retail_5d131e8ff2fd6390 | 8 351  | 6 671 (80%)   | 8 351 (100%)  | 1 166 (14%)   | 6 858 (82%)   | 7 667 (92%)   | 7 850 (94%)     | 7 242 (87%)     | 6 766 (81%)       | 6 548 (78%)            | 6 611 (79%)    |
| Health_0676356d6ba137b6 | 12 100 | 6 762 (56%)   | 12 100 (100%) | 12 100 (100%) | 12 100 (100%) | 11 109 (92%)  | 11 924 (99%)    | 10 906 (90%)    | 11 527 (95%)      | 11 348 (94%)           | 11 559 (96%)   |
| Travel_3724963d1920e16a | 3 317  | 343 (10%)     | 2 407 (73%)   | 3 317 (100%)  | 2 513 (76%)   | 3 046 (92%)   | 2 751 (83%)     | 3 072 (93%)     | 2 801 (84%)       | 2 776 (84%)            | 2 826 (85%)    |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.4%, revenue -3.4%
- **A3 vs best_price**: impressions +0.2%, revenue -3.8%
- **A2 stability**: moderate (spread 7.8%)
- **A3 stability**: moderate (spread 8.5%)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 12 Scenario : Company 10, 100K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 10 |
| Requests | 100 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 1 480 304 impressions |
| Total budget (A3) | 283 426 260 units. |
| Mean CPM | 192.0 |

#### Participating companies

| Campaign        | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| --------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 180 120     | 50 433 600  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 259 350     | 41 496 000  |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 208 050     | 29 127 000  |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 74 654      | 6 718 860   |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 109 440     | 27 360 000  |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 201 450     | 40 290 000  |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 123 120     | 39 398 400  |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 113 880     | 14 804 400  |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 165 000     | 24 750 000  |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 45 240      | 9 048 000   |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | ---------- | ------------ |
| best_one          | 99 662 | 99.7%     | 0.3%      | 23 419 980 | 235.0        |
| random_one        | 99 662 | 99.7%     | 0.3%      | 18 391 890 | 184.5        |
| best_price        | 99 662 | 99.7%     | 0.3%      | 25 779 600 | 258.7        |
| random_price      | 99 662 | 99.7%     | 0.3%      | 19 770 290 | 198.4        |
| best_velocity     | 99 662 | 99.7%     | 0.3%      | 19 081 770 | 191.5        |
| random_velocity   | 99 662 | 99.7%     | 0.3%      | 18 400 120 | 184.6        |
| best_heuristics   | 99 662 | 99.7%     | 0.3%      | 25 188 800 | 252.7        |
| random_heuristics | 99 662 | 99.7%     | 0.3%      | 20 302 670 | 203.7        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 662     | 99 662     | 99 662     | 99 662     |
| Fill rate | 99.7%      | 99.7%      | 99.7%      | 99.7%      |
| Revenue   | 14 405 510 | 25 779 600 | 23 619 100 | 23 102 160 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 662     | 99 662     | 99 662     | 99 662     |
| Fill rate | 99.7%      | 99.7%      | 99.7%      | 99.7%      |
| Revenue   | 15 167 740 | 25 779 600 | 23 596 420 | 23 060 005 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad      | Volume  | best_one     | random_one  | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| --------------- | ------- | ------------ | ----------- | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 180 120 | 60 010 (33%) | 10 015 (6%) | 19 228 (11%) | 13 692 (8%)  | 12 127 (7%)   | 9 999 (6%)      | 33 998 (19%)    | 16 122 (9%)       | 21 070 (12%)           | 22 585 (13%)   |
| Telecom_d46ed517452394a2 | 259 350 | 29 483 (11%) | 18 632 (7%) | 20 605 (8%)  | 17 578 (7%)  | 17 461 (7%)   | 18 705 (7%)     | 20 605 (8%)     | 18 145 (7%)       | 14 254 (5%)            | 14 734 (6%)    |
| Retail_59c52779836b2bae | 208 050 | 0 (0%)       | 14 376 (7%) | 0 (0%)       | 12 164 (6%)  | 14 008 (7%)   | 14 328 (7%)     | 0 (0%)          | 11 131 (5%)       | 7 101 (3%)             | 6 800 (3%)     |
| Campaign_51288482374d537c | 74 654  | 0 (0%)       | 4 895 (7%)  | 0 (0%)       | 2 873 (4%)   | 5 026 (7%)    | 4 898 (7%)      | 0 (0%)          | 2 361 (3%)        | 517 (1%)               | 461 (1%)       |
| Automotive_9e1edff89ac9a790 | 109 440 | 357 (0%)     | 6 902 (6%)  | 7 673 (7%)   | 8 580 (8%)   | 7 368 (7%)    | 6 977 (6%)      | 7 673 (7%)      | 9 219 (8%)        | 12 109 (11%)           | 10 604 (10%)   |
| Campaign_4d4dc901c2e49788 | 201 450 | 7 065 (4%)   | 13 430 (7%) | 7 065 (4%)   | 13 869 (7%)  | 13 562 (7%)   | 13 455 (7%)     | 7 065 (4%)      | 13 727 (7%)       | 10 903 (5%)            | 10 788 (5%)    |
| Property_5a34d256a53751c3 | 123 120 | 0 (0%)       | 6 321 (5%)  | 40 782 (33%) | 9 536 (8%)   | 8 289 (7%)    | 6 346 (5%)      | 26 012 (21%)    | 10 136 (8%)       | 20 920 (17%)           | 20 320 (17%)   |
| Retail_5d131e8ff2fd6390 | 113 880 | 720 (1%)     | 8 157 (7%)  | 534 (0%)     | 6 740 (6%)   | 7 667 (7%)    | 8 168 (7%)      | 534 (0%)        | 5 592 (5%)        | 3 011 (3%)             | 3 119 (3%)     |
| Health_0676356d6ba137b6 | 165 000 | 2 027 (1%)   | 14 561 (9%) | 2 139 (1%)   | 12 200 (7%)  | 11 108 (7%)   | 14 483 (9%)     | 2 139 (1%)      | 11 039 (7%)       | 7 355 (4%)             | 7 628 (5%)     |
| Travel_3724963d1920e16a | 45 240  | 0 (0%)       | 2 373 (5%)  | 1 636 (4%)   | 2 430 (5%)   | 3 046 (7%)    | 2 303 (5%)      | 1 636 (4%)      | 2 190 (5%)        | 2 416 (5%)             | 2 619 (6%)     |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -10.4%
- **A3 vs best_price**: impressions +0.0%, revenue -10.5%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
## 13 Scenario: Company 20, 10K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 20 |
| Requests | 10 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 53 706 impressions |
| Total budget (A3) | 9 256 400 units. |
| Mean CPM | 165.5 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 4 202       | 1 176 560   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 6 051       | 968 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 4 854       | 679 560     |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 1 741       | 156 690     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 2 553       | 638 250     |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 4 700       | 940 000     |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 2 872       | 919 040     |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 2 657       | 345 410     |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 3 849       | 577 350     |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 1 055       | 211 000     |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 1 378       | 275 600     |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 1 021       | 163 360     |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 919         | 101 090     |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 2 646       | 211 680     |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 755         | 75 500      |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 2 017       | 242 040     |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 2 111       | 211 100     |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 3 207       | 545 190     |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 1 968       | 472 320     |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 3 150       | 346 500     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 10 000 | 100.0%    | 0.0%      | 2 135 890 | 213.6        |
| random_one        | 10 000 | 100.0%    | 0.0%      | 1 662 180 | 166.2        |
| best_price        | 10 000 | 100.0%    | 0.0%      | 2 539 210 | 253.9        |
| random_price      | 10 000 | 100.0%    | 0.0%      | 1 852 870 | 185.3        |
| best_velocity     | 10 000 | 100.0%    | 0.0%      | 1 723 360 | 172.3        |
| random_velocity   | 10 000 | 100.0%    | 0.0%      | 1 684 100 | 168.4        |
| best_heuristics   | 10 000 | 100.0%    | 0.0%      | 2 380 360 | 238.0        |
| random_heuristics | 10 000 | 100.0%    | 0.0%      | 1 909 420 | 190.9        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 937     | 10 000    | 10 000    | 10 000    |
| Fill rate | 99.4%     | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 480 990 | 2 538 970 | 2 260 135 | 2 230 498 |

> Distribution of impressions: 63 (0.6% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 937     | 10 000    | 10 000    | 10 000    |
| Fill rate | 99.4%     | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 596 490 | 2 538 330 | 2 264 395 | 2 237 806 |

> Distribution of impressions: 63 (0.6% from average)

#### Advertising displays (impressions (disposal volume))

| Ad       | Volume | best_one     | random_one  | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ---------------- | ------ | ------------ | ----------- | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 4 202  | 4 202 (100%) | 650 (15%)   | 3 179 (76%)  | 999 (24%)    | 782 (19%)     | 653 (16%)       | 2 402 (57%)     | 1 207 (29%)       | 2 020 (48%)            | 2 015 (48%)    |
| Telecom_d46ed517452394a2 | 6 051  | 4 617 (76%)  | 1 273 (21%) | 1 986 (33%)  | 1 266 (21%)  | 1 126 (19%)   | 1 280 (21%)     | 1 576 (26%)     | 1 323 (22%)       | 1 138 (19%)            | 1 239 (20%)    |
| Retail_59c52779836b2bae | 4 854  | 0 (0%)       | 915 (19%)   | 0 (0%)       | 804 (17%)    | 904 (19%)     | 889 (18%)       | 166 (3%)        | 811 (17%)         | 563 (12%)              | 569 (12%)      |
| Campaign_51288482374d537c | 1 741  | 0 (0%)       | 286 (16%)   | 0 (0%)       | 180 (10%)    | 324 (19%)     | 296 (17%)       | 0 (0%)          | 160 (9%)          | 20 (1%)                | 18 (1%)        |
| Automotive_9e1edff89ac9a790 | 2 553  | 77 (3%)      | 455 (18%)   | 758 (30%)    | 679 (27%)    | 475 (19%)     | 494 (19%)       | 1 192 (47%)     | 725 (28%)         | 1 056 (41%)            | 1 034 (41%)    |
| Campaign_4d4dc901c2e49788 | 4 700  | 767 (16%)    | 928 (20%)   | 721 (15%)    | 1 130 (24%)  | 875 (19%)     | 962 (20%)       | 1 176 (25%)     | 1 138 (24%)       | 1 125 (24%)            | 1 186 (25%)    |
| Property_5a34d256a53751c3 | 2 872  | 0 (0%)       | 377 (13%)   | 2 872 (100%) | 703 (24%)    | 535 (19%)     | 432 (15%)       | 1 676 (58%)     | 785 (27%)         | 1 505 (52%)            | 1 528 (53%)    |
| Retail_5d131e8ff2fd6390 | 2 657  | 80 (3%)      | 492 (19%)   | 43 (2%)      | 466 (18%)    | 495 (19%)     | 515 (19%)       | 43 (2%)         | 398 (15%)         | 270 (10%)              | 244 (9%)       |
| Health_0676356d6ba137b6 | 3 849  | 227 (6%)     | 1 268 (33%) | 239 (6%)     | 1 119 (29%)  | 717 (19%)     | 1 223 (32%)     | 350 (9%)        | 1 009 (26%)       | 801 (21%)              | 732 (19%)      |
| Travel_3724963d1920e16a | 1 055  | 0 (0%)       | 134 (13%)   | 152 (14%)    | 188 (18%)    | 196 (19%)     | 162 (15%)       | 152 (14%)       | 181 (17%)         | 217 (21%)              | 219 (21%)      |
| Bank_93461467de106ae8 | 1 378  | 0 (0%)       | 179 (13%)   | 0 (0%)       | 187 (14%)    | 257 (19%)     | 162 (12%)       | 345 (25%)       | 183 (13%)         | 116 (8%)               | 101 (7%)       |
| Retail_6162b5875d2e4e9b | 1 021  | 5 (0%)       | 180 (18%)   | 25 (2%)      | 169 (17%)    | 190 (19%)     | 166 (16%)       | 158 (15%)       | 169 (17%)         | 186 (18%)              | 166 (16%)      |
| Retail_8846b13f4335d7b7 | 919    | 7 (1%)       | 168 (18%)   | 7 (1%)       | 138 (15%)    | 171 (19%)     | 169 (18%)       | 5 (1%)          | 119 (13%)         | 36 (4%)                | 32 (4%)        |
| Campaign_a54822eb2c43abe7 | 2 646  | 0 (0%)       | 479 (18%)   | 0 (0%)       | 243 (9%)     | 493 (19%)     | 502 (19%)       | 0 (0%)          | 202 (8%)          | 23 (1%)                | 19 (1%)        |
| Campaign_04055ec242bc0613 | 755    | 4 (1%)       | 131 (17%)   | 0 (0%)       | 95 (13%)     | 141 (19%)     | 139 (18%)       | 0 (0%)          | 79 (10%)          | 20 (3%)                | 16 (2%)        |
| Property_db25972d5f786d2e | 2 017  | 0 (0%)       | 294 (15%)   | 0 (0%)       | 168 (8%)     | 376 (19%)     | 278 (14%)       | 0 (0%)          | 157 (8%)          | 5 (0%)                 | 3 (0%)         |
| Children_90daa9b022baf620 | 2 111  | 0 (0%)       | 383 (18%)   | 0 (0%)       | 208 (10%)    | 393 (19%)     | 327 (15%)       | 0 (0%)          | 194 (9%)          | 15 (1%)                | 14 (1%)        |
| Travel_a0a6420a0d37809f | 3 207  | 0 (0%)       | 444 (14%)   | 0 (0%)       | 420 (13%)    | 597 (19%)     | 455 (14%)       | 0 (0%)          | 385 (12%)         | 243 (8%)               | 204 (6%)       |
| Bank_fbe065970201fb55 | 1 968  | 0 (0%)       | 247 (13%)   | 0 (0%)       | 323 (16%)    | 366 (19%)     | 268 (14%)       | 739 (38%)       | 329 (17%)         | 443 (23%)              | 470 (24%)      |
| Campaign_d5e7563f29a5b384 | 3 150  | 14 (0%)      | 717 (23%)   | 18 (1%)      | 515 (16%)    | 587 (19%)     | 628 (20%)       | 20 (1%)         | 446 (14%)         | 187 (6%)               | 182 (6%)       |


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.0%, revenue -12.2%
- **A3 vs best_price**: impressions -0.0%, revenue -11.9%
- **A2 stability**: high (0.6% scatter)
- **A3 stability**: high (0.6% scatter)

---
## 14 Scenario: Company 20, 10K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 20 |
| Requests | 10 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 16 874 impressions |
| Total budget (A3) | 2 908 170 units. |
| Mean CPM | 165.5 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 1 320       | 369 600     |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 1 901       | 304 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 1 525       | 213 500     |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 547         | 49 230      |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 802         | 200 500     |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 1 477       | 295 400     |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 902         | 288 640     |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 835         | 108 550     |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 1 210       | 181 500     |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 331         | 66 200      |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 433         | 86 600      |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 321         | 51 360      |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 289         | 31 790      |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 831         | 66 480      |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 237         | 23 700      |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 634         | 76 080      |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 663         | 66 300      |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 1 008       | 171 360     |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 618         | 148 320     |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 990         | 108 900     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 10 000 | 100.0%    | 0.0%      | 1 886 650 | 188.7        |
| random_one        | 9 994  | 99.9%     | 0.1%      | 1 664 570 | 166.6        |
| best_price        | 10 000 | 100.0%    | 0.0%      | 2 106 150 | 210.6        |
| random_price      | 10 000 | 100.0%    | 0.0%      | 1 852 870 | 185.3        |
| best_velocity     | 10 000 | 100.0%    | 0.0%      | 1 723 330 | 172.3        |
| random_velocity   | 10 000 | 100.0%    | 0.0%      | 1 694 890 | 169.5        |
| best_heuristics   | 10 000 | 100.0%    | 0.0%      | 1 923 540 | 192.4        |
| random_heuristics | 10 000 | 100.0%    | 0.0%      | 1 855 140 | 185.5        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 537     | 10 000    | 9 939     | 9 915     |
| Fill rate | 95.4%     | 100.0%    | 99.4%     | 99.1%     |
| Revenue   | 1 493 060 | 2 093 400 | 1 907 070 | 1 894 838 |

> Distribution of impressions: 463 (4.7% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 548     | 10 000    | 9 950     | 9 918     |
| Fill rate | 95.5%     | 100.0%    | 99.5%     | 99.2%     |
| Revenue   | 1 500 780 | 2 108 000 | 1 914 580 | 1 900 164 |

> Distribution of impressions: 452 (4.6% from average)

#### Advertising displays (impressions (disposal volume))

| Ad       | Volume | best_one     | random_one   | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ---------------- | ------ | ------------ | ------------ | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 1 320  | 1 320 (100%) | 654 (50%)    | 1 320 (100%) | 999 (76%)    | 782 (59%)     | 691 (52%)       | 1 121 (85%)     | 1 058 (80%)       | 1 057 (80%)            | 1 087 (82%)    |
| Telecom_d46ed517452394a2 | 1 901  | 1 901 (100%) | 1 271 (67%)  | 1 901 (100%) | 1 266 (67%)  | 1 126 (59%)   | 1 256 (66%)     | 1 272 (67%)     | 1 305 (69%)       | 1 238 (65%)            | 1 260 (66%)    |
| Retail_59c52779836b2bae | 1 525  | 1 525 (100%) | 919 (60%)    | 292 (19%)    | 804 (53%)    | 903 (59%)     | 890 (58%)       | 865 (57%)       | 833 (55%)         | 860 (56%)              | 850 (56%)      |
| Campaign_51288482374d537c | 547    | 547 (100%)   | 283 (52%)    | 0 (0%)       | 180 (33%)    | 324 (59%)     | 309 (56%)       | 117 (21%)       | 205 (37%)         | 80 (15%)               | 78 (14%)       |
| Automotive_9e1edff89ac9a790 | 802    | 802 (100%)   | 463 (58%)    | 802 (100%)   | 679 (85%)    | 475 (59%)     | 500 (62%)       | 651 (81%)       | 644 (80%)         | 612 (76%)              | 619 (77%)      |
| Campaign_4d4dc901c2e49788 | 1 477  | 1 477 (100%) | 938 (64%)    | 1 477 (100%) | 1 130 (77%)  | 875 (59%)     | 959 (65%)       | 1 086 (74%)     | 1 074 (73%)       | 1 147 (78%)            | 1 138 (77%)    |
| Property_5a34d256a53751c3 | 902    | 665 (74%)    | 380 (42%)    | 902 (100%)   | 703 (78%)    | 535 (59%)     | 460 (51%)       | 770 (85%)       | 698 (77%)         | 745 (83%)              | 739 (82%)      |
| Retail_5d131e8ff2fd6390 | 835    | 697 (83%)    | 492 (59%)    | 43 (5%)      | 466 (56%)    | 495 (59%)     | 520 (62%)       | 381 (46%)       | 435 (52%)         | 420 (50%)              | 419 (50%)      |
| Health_0676356d6ba137b6 | 1 210  | 707 (58%)    | 1 210 (100%) | 831 (69%)    | 1 119 (92%)  | 717 (59%)     | 1 034 (85%)     | 722 (60%)       | 957 (79%)         | 987 (82%)              | 986 (81%)      |
| Travel_3724963d1920e16a | 331    | 31 (9%)      | 134 (40%)    | 331 (100%)   | 188 (57%)    | 196 (59%)     | 167 (50%)       | 231 (70%)       | 190 (57%)         | 213 (64%)              | 221 (67%)      |
| Bank_93461467de106ae8 | 433    | 0 (0%)       | 187 (43%)    | 433 (100%)   | 187 (43%)    | 257 (59%)     | 188 (43%)       | 319 (74%)       | 214 (49%)         | 288 (67%)              | 274 (63%)      |
| Retail_6162b5875d2e4e9b | 321    | 69 (21%)     | 179 (56%)    | 121 (38%)    | 169 (53%)    | 190 (59%)     | 175 (55%)       | 200 (62%)       | 170 (53%)         | 187 (58%)              | 182 (57%)      |
| Retail_8846b13f4335d7b7 | 289    | 58 (20%)     | 168 (58%)    | 8 (3%)       | 138 (48%)    | 172 (60%)     | 165 (57%)       | 104 (36%)       | 137 (47%)         | 96 (34%)               | 89 (31%)       |
| Campaign_a54822eb2c43abe7 | 831    | 36 (4%)      | 485 (58%)    | 0 (0%)       | 243 (29%)    | 493 (59%)     | 512 (62%)       | 97 (12%)        | 277 (33%)         | 131 (16%)              | 139 (17%)      |
| Campaign_04055ec242bc0613 | 237    | 19 (8%)      | 134 (57%)    | 0 (0%)       | 95 (40%)     | 141 (59%)     | 138 (58%)       | 70 (30%)        | 94 (40%)          | 55 (24%)               | 51 (22%)       |
| Property_db25972d5f786d2e | 634    | 34 (5%)      | 293 (46%)    | 0 (0%)       | 168 (26%)    | 376 (59%)     | 304 (48%)       | 314 (50%)       | 199 (31%)         | 228 (36%)              | 210 (33%)      |
| Children_90daa9b022baf620 | 663    | 0 (0%)       | 385 (58%)    | 0 (0%)       | 208 (31%)    | 393 (59%)     | 353 (53%)       | 195 (29%)       | 227 (34%)         | 135 (20%)              | 133 (20%)      |
| Travel_a0a6420a0d37809f | 1 008  | 0 (0%)       | 450 (45%)    | 901 (89%)    | 420 (42%)    | 597 (59%)     | 471 (47%)       | 649 (64%)       | 446 (44%)         | 602 (60%)              | 606 (60%)      |
| Bank_fbe065970201fb55 | 618    | 0 (0%)       | 256 (41%)    | 618 (100%)   | 323 (52%)    | 366 (59%)     | 290 (47%)       | 482 (78%)       | 359 (58%)         | 444 (72%)              | 451 (73%)      |
| Campaign_d5e7563f29a5b384 | 990    | 112 (11%)    | 713 (72%)    | 20 (2%)      | 515 (52%)    | 587 (59%)     | 618 (62%)       | 354 (36%)       | 478 (48%)         | 380 (38%)              | 377 (38%)      |


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.9%, revenue -10.0%
- **A3 vs best_price**: impressions -0.8%, revenue -9.8%
- **A2 stability**: high (4.7% scatter)
- **A3 stability**: high (4.6% scatter)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 15 Scenario : Company 20, 10K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 20 |
| Requests | 10 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 230 215 impressions |
| Total budget (A3) | 39 678 570 units. |
| Mean CPM | 165.5 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 18 012      | 5 043 360   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 25 935      | 4 149 600   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 20 805      | 2 912 700   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 7 465       | 671 850     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 10 944      | 2 736 000   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 20 145      | 4 029 000   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 12 312      | 3 939 840   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 11 388      | 1 480 440   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 16 500      | 2 475 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 4 524       | 904 800     |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 5 909       | 1 181 800   |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 4 380       | 700 800     |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 3 942       | 433 620     |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 11 340      | 907 200     |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 3 239       | 323 900     |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 8 645       | 1 037 400   |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 9 048       | 904 800     |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 13 746      | 2 336 820   |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 8 436       | 2 024 640   |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 13 500      | 1 485 000   |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 10 000 | 100.0%    | 0.0%      | 2 351 970 | 235.2        |
| random_one        | 10 000 | 100.0%    | 0.0%      | 1 662 180 | 166.2        |
| best_price        | 10 000 | 100.0%    | 0.0%      | 2 589 930 | 259.0        |
| random_price      | 10 000 | 100.0%    | 0.0%      | 1 852 870 | 185.3        |
| best_velocity     | 10 000 | 100.0%    | 0.0%      | 1 723 470 | 172.3        |
| random_velocity   | 10 000 | 100.0%    | 0.0%      | 1 680 390 | 168.0        |
| best_heuristics   | 10 000 | 100.0%    | 0.0%      | 2 529 170 | 252.9        |
| random_heuristics | 10 000 | 100.0%    | 0.0%      | 1 917 680 | 191.8        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 10 000    | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 473 450 | 2 589 690 | 2 347 065 | 2 298 142 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 10 000    | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 595 400 | 2 589 070 | 2 351 230 | 2 301 945 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad       | Volume | best_one    | random_one | best_price  | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ---------------- | ------ | ----------- | ---------- | ----------- | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 18 012 | 6 051 (34%) | 650 (4%)   | 1 911 (11%) | 999 (6%)     | 782 (4%)      | 642 (4%)        | 3 430 (19%)     | 1 235 (7%)        | 2 166 (12%)            | 2 172 (12%)    |
| Telecom_d46ed517452394a2 | 25 935 | 2 858 (11%) | 1 273 (5%) | 1 986 (8%)  | 1 266 (5%)   | 1 126 (4%)    | 1 290 (5%)      | 1 986 (8%)      | 1 336 (5%)        | 1 088 (4%)             | 1 161 (4%)     |
| Retail_59c52779836b2bae | 20 805 | 0 (0%)      | 915 (4%)   | 0 (0%)      | 804 (4%)     | 903 (4%)      | 879 (4%)        | 0 (0%)          | 794 (4%)          | 544 (3%)               | 546 (3%)       |
| Campaign_51288482374d537c | 7 465  | 0 (0%)      | 286 (4%)   | 0 (0%)      | 180 (2%)     | 324 (4%)      | 296 (4%)        | 0 (0%)          | 168 (2%)          | 20 (0%)                | 18 (0%)        |
| Automotive_9e1edff89ac9a790 | 10 944 | 33 (0%)     | 455 (4%)   | 758 (7%)    | 679 (6%)     | 475 (4%)      | 490 (4%)        | 758 (7%)        | 743 (7%)          | 1 037 (9%)             | 1 020 (9%)     |
| Campaign_4d4dc901c2e49788 | 20 145 | 721 (4%)    | 928 (5%)   | 721 (4%)    | 1 130 (6%)   | 875 (4%)      | 961 (5%)        | 721 (4%)        | 1 145 (6%)        | 940 (5%)               | 1 030 (5%)     |
| Property_5a34d256a53751c3 | 12 312 | 0 (0%)      | 377 (3%)   | 4 140 (34%) | 703 (6%)     | 535 (4%)      | 425 (3%)        | 2 621 (21%)     | 795 (6%)          | 1 924 (16%)            | 1 914 (16%)    |
| Retail_5d131e8ff2fd6390 | 11 388 | 80 (1%)     | 492 (4%)   | 43 (0%)     | 466 (4%)     | 495 (4%)      | 516 (5%)        | 43 (0%)         | 390 (3%)          | 263 (2%)               | 240 (2%)       |
| Health_0676356d6ba137b6 | 16 500 | 227 (1%)    | 1 268 (8%) | 239 (1%)    | 1 119 (7%)   | 716 (4%)      | 1 270 (8%)      | 239 (1%)        | 1 018 (6%)        | 756 (5%)               | 695 (4%)       |
| Travel_3724963d1920e16a | 4 524  | 0 (0%)      | 134 (3%)   | 152 (3%)    | 188 (4%)     | 196 (4%)      | 155 (3%)        | 152 (3%)        | 182 (4%)          | 192 (4%)               | 193 (4%)       |
| Bank_93461467de106ae8 | 5 909  | 0 (0%)      | 179 (3%)   | 0 (0%)      | 187 (3%)     | 257 (4%)      | 161 (3%)        | 0 (0%)          | 180 (3%)          | 77 (1%)                | 69 (1%)        |
| Retail_6162b5875d2e4e9b | 4 380  | 5 (0%)      | 180 (4%)   | 25 (1%)     | 169 (4%)     | 191 (4%)      | 163 (4%)        | 25 (1%)         | 171 (4%)          | 175 (4%)               | 158 (4%)       |
| Retail_8846b13f4335d7b7 | 3 942  | 7 (0%)      | 168 (4%)   | 7 (0%)      | 138 (4%)     | 172 (4%)      | 168 (4%)        | 5 (0%)          | 115 (3%)          | 36 (1%)                | 31 (1%)        |
| Campaign_a54822eb2c43abe7 | 11 340 | 0 (0%)      | 479 (4%)   | 0 (0%)      | 243 (2%)     | 493 (4%)      | 498 (4%)        | 0 (0%)          | 196 (2%)          | 22 (0%)                | 18 (0%)        |
| Campaign_04055ec242bc0613 | 3 239  | 4 (0%)      | 131 (4%)   | 0 (0%)      | 95 (3%)      | 141 (4%)      | 141 (4%)        | 0 (0%)          | 73 (2%)           | 20 (1%)                | 16 (1%)        |
| Property_db25972d5f786d2e | 8 645  | 0 (0%)      | 294 (3%)   | 0 (0%)      | 168 (2%)     | 376 (4%)      | 281 (3%)        | 0 (0%)          | 147 (2%)          | 0 (0%)                 | 1 (0%)         |
| Children_90daa9b022baf620 | 9 048  | 0 (0%)      | 383 (4%)   | 0 (0%)      | 208 (2%)     | 393 (4%)      | 321 (4%)        | 0 (0%)          | 180 (2%)          | 14 (0%)                | 14 (0%)        |
| Travel_a0a6420a0d37809f | 13 746 | 0 (0%)      | 444 (3%)   | 0 (0%)      | 420 (3%)     | 597 (4%)      | 449 (3%)        | 0 (0%)          | 369 (3%)          | 166 (1%)               | 140 (1%)       |
| Bank_fbe065970201fb55 | 8 436  | 0 (0%)      | 247 (3%)   | 0 (0%)      | 323 (4%)     | 367 (4%)      | 262 (3%)        | 0 (0%)          | 320 (4%)          | 369 (4%)               | 377 (4%)       |
| Campaign_d5e7563f29a5b384 | 13 500 | 14 (0%)     | 717 (5%)   | 18 (0%)     | 515 (4%)     | 586 (4%)      | 632 (5%)        | 20 (0%)         | 443 (3%)          | 183 (1%)               | 177 (1%)       |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -11.3%
- **A3 vs best_price**: impressions +0.0%, revenue -11.1%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
## 16 Scenario: Company 20, 100K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 20 |
| Requests | 100 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 537 169 impressions |
| Total budget (A3) | 92 583 410 units. |
| Mean CPM | 165.5 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 42 028      | 11 767 840  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 60 514      | 9 682 240   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 48 545      | 6 796 300   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 17 419      | 1 567 710   |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 25 536      | 6 384 000   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 47 005      | 9 401 000   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 28 728      | 9 192 960   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 26 572      | 3 454 360   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 38 500      | 5 775 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 10 556      | 2 111 200   |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 13 789      | 2 757 800   |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 10 219      | 1 635 040   |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 9 197       | 1 011 670   |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 26 460      | 2 116 800   |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 7 559       | 755 900     |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 20 173      | 2 420 760   |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 21 112      | 2 111 200   |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 32 074      | 5 452 580   |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 19 684      | 4 724 160   |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 31 499      | 3 464 890   |

#### Classical Strategies (1 run)

| Strategy         | Impressions  | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------- | --------- | --------- | ---------- | ------------ |
| best_one          | 100 000 | 100.0%    | 0.0%      | 21 356 980 | 213.6        |
| random_one        | 100 000 | 100.0%    | 0.0%      | 16 756 700 | 167.6        |
| best_price        | 100 000 | 100.0%    | 0.0%      | 25 341 970 | 253.4        |
| random_price      | 100 000 | 100.0%    | 0.0%      | 18 417 270 | 184.2        |
| best_velocity     | 100 000 | 100.0%    | 0.0%      | 17 235 370 | 172.4        |
| random_velocity   | 100 000 | 100.0%    | 0.0%      | 16 788 890 | 167.9        |
| best_heuristics   | 100 000 | 100.0%    | 0.0%      | 23 759 800 | 237.6        |
| random_heuristics | 100 000 | 100.0%    | 0.0%      | 18 960 760 | 189.6        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 408     | 100 000    | 100 000    | 99 998     |
| Fill rate | 99.4%      | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 14 902 230 | 25 332 380 | 22 519 885 | 22 305 764 |

> Distribution of impressions: 592 (0.6% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 730     | 100 000    | 100 000    | 99 999     |
| Fill rate | 99.7%      | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 16 040 030 | 25 332 380 | 22 573 310 | 22 176 215 |

> Distribution of impressions: 270 (0.3% from average)

#### Advertising displays (impressions (disposal volume))

| Ad       | Volume | best_one      | random_one   | best_price    | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ---------------- | ------ | ------------- | ------------ | ------------- | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 42 028 | 42 028 (100%) | 6 626 (16%)  | 31 282 (74%)  | 10 168 (24%) | 7 824 (19%)   | 6 684 (16%)     | 23 923 (57%)    | 12 102 (29%)      | 19 758 (47%)           | 19 547 (47%)   |
| Telecom_d46ed517452394a2 | 60 514 | 46 605 (77%)  | 12 921 (21%) | 20 605 (34%)  | 12 918 (21%) | 11 265 (19%)  | 12 876 (21%)    | 15 976 (26%)    | 13 727 (23%)      | 12 972 (21%)           | 13 681 (23%)   |
| Retail_59c52779836b2bae | 48 545 | 0 (0%)        | 9 295 (19%)  | 0 (0%)        | 8 552 (18%)  | 9 037 (19%)   | 9 265 (19%)     | 1 879 (4%)      | 8 331 (17%)       | 5 955 (12%)            | 5 604 (12%)    |
| Campaign_51288482374d537c | 17 419 | 0 (0%)        | 2 788 (16%)  | 0 (0%)        | 1 940 (11%)  | 3 243 (19%)   | 2 948 (17%)     | 0 (0%)          | 1 719 (10%)       | 194 (1%)               | 163 (1%)       |
| Automotive_9e1edff89ac9a790 | 25 536 | 756 (3%)      | 4 780 (19%)  | 7 673 (30%)   | 6 486 (25%)  | 4 754 (19%)   | 4 793 (19%)     | 11 849 (46%)    | 7 071 (28%)       | 10 768 (42%)           | 9 828 (38%)    |
| Campaign_4d4dc901c2e49788 | 47 005 | 7 526 (16%)   | 9 391 (20%)  | 7 065 (15%)   | 10 870 (23%) | 8 750 (19%)   | 9 554 (20%)     | 11 569 (25%)    | 11 021 (23%)      | 12 728 (27%)           | 11 038 (23%)   |
| Property_5a34d256a53751c3 | 28 728 | 0 (0%)        | 4 002 (14%)  | 28 728 (100%) | 6 703 (23%)  | 5 348 (19%)   | 4 093 (14%)     | 16 696 (58%)    | 7 327 (26%)       | 14 799 (52%)           | 15 215 (53%)   |
| Retail_5d131e8ff2fd6390 | 26 572 | 720 (3%)      | 4 983 (19%)  | 421 (2%)      | 4 456 (17%)  | 4 947 (19%)   | 5 010 (19%)     | 421 (2%)        | 3 835 (14%)       | 2 422 (9%)             | 2 636 (10%)    |
| Health_0676356d6ba137b6 | 38 500 | 2 027 (5%)    | 12 150 (32%) | 2 098 (5%)    | 10 892 (28%) | 7 167 (19%)   | 11 629 (30%)    | 3 449 (9%)      | 9 921 (26%)       | 7 198 (19%)            | 7 085 (18%)    |
| Travel_3724963d1920e16a | 10 556 | 0 (0%)        | 1 549 (15%)  | 1 636 (15%)   | 1 846 (17%)  | 1 965 (19%)   | 1 549 (15%)     | 1 636 (15%)     | 1 737 (16%)       | 2 303 (22%)            | 2 641 (25%)    |
| Bank_93461467de106ae8 | 13 789 | 0 (0%)        | 1 647 (12%)  | 0 (0%)        | 1 734 (13%)  | 2 567 (19%)   | 1 718 (12%)     | 3 394 (25%)     | 1 795 (13%)       | 1 233 (9%)             | 1 318 (10%)    |
| Retail_6162b5875d2e4e9b | 10 219 | 71 (1%)       | 1 796 (18%)  | 225 (2%)      | 1 869 (18%)  | 1 903 (19%)   | 1 796 (18%)     | 1 624 (16%)     | 1 800 (18%)       | 2 156 (21%)            | 2 100 (21%)    |
| Retail_8846b13f4335d7b7 | 9 197  | 64 (1%)       | 1 615 (18%)  | 64 (1%)       | 1 239 (13%)  | 1 713 (19%)   | 1 625 (18%)     | 57 (1%)         | 1 074 (12%)       | 289 (3%)               | 407 (4%)       |
| Campaign_a54822eb2c43abe7 | 26 460 | 0 (0%)        | 4 708 (18%)  | 0 (0%)        | 2 491 (9%)   | 4 925 (19%)   | 4 818 (18%)     | 0 (0%)          | 2 156 (8%)        | 106 (0%)               | 191 (1%)       |
| Campaign_04055ec242bc0613 | 7 559  | 24 (0%)       | 1 406 (19%)  | 0 (0%)        | 991 (13%)    | 1 407 (19%)   | 1 396 (18%)     | 0 (0%)          | 884 (12%)         | 132 (2%)               | 215 (3%)       |
| Property_db25972d5f786d2e | 20 173 | 0 (0%)        | 2 884 (14%)  | 0 (0%)        | 1 838 (9%)   | 3 755 (19%)   | 2 950 (15%)     | 0 (0%)          | 1 639 (8%)        | 22 (0%)                | 35 (0%)        |
| Children_90daa9b022baf620 | 21 112 | 0 (0%)        | 3 501 (17%)  | 0 (0%)        | 2 226 (11%)  | 3 931 (19%)   | 3 468 (16%)     | 0 (0%)          | 1 925 (9%)        | 179 (1%)               | 209 (1%)       |
| Travel_a0a6420a0d37809f | 32 074 | 0 (0%)        | 4 484 (14%)  | 0 (0%)        | 4 206 (13%)  | 5 971 (19%)   | 4 477 (14%)     | 0 (0%)          | 3 956 (12%)       | 1 249 (4%)             | 2 377 (7%)     |
| Bank_fbe065970201fb55 | 19 684 | 0 (0%)        | 2 582 (13%)  | 0 (0%)        | 3 283 (17%)  | 3 664 (19%)   | 2 656 (13%)     | 7 317 (37%)     | 3 374 (17%)       | 4 086 (21%)            | 3 914 (20%)    |
| Campaign_d5e7563f29a5b384 | 31 499 | 179 (1%)      | 6 892 (22%)  | 203 (1%)      | 5 292 (17%)  | 5 864 (19%)   | 6 695 (21%)     | 210 (1%)        | 4 606 (15%)       | 1 440 (5%)             | 1 784 (6%)     |


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.0%, revenue -12.0%
- **A3 vs best_price**: impressions -0.0%, revenue -12.5%
- **A2 stability**: high (0.6% scatter)
- **A3 stability**: high (0.3% scatter)

---
## 17 Scenario: Company 20, 100K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 20 |
| Requests | 100 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 168 817 impressions |
| Total budget (A3) | 29 096 230 units. |
| Mean CPM | 165.5 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 13 208      | 3 698 240   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 19 019      | 3 043 040   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 15 257      | 2 135 980   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 5 474       | 492 660     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 8 025       | 2 006 250   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 14 773      | 2 954 600   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 9 028       | 2 888 960   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 8 351       | 1 085 630   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 12 100      | 1 815 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 3 317       | 663 400     |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 4 333       | 866 600     |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 3 211       | 513 760     |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 2 890       | 317 900     |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 8 316       | 665 280     |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 2 375       | 237 500     |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 6 340       | 760 800     |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 6 635       | 663 500     |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 10 080      | 1 713 600   |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 6 186       | 1 484 640   |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 9 899       | 1 088 890   |

#### Classical Strategies (1 run)

| Strategy         | Impressions  | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------- | --------- | --------- | ---------- | ------------ |
| best_one          | 100 000 | 100.0%    | 0.0%      | 18 964 640 | 189.6        |
| random_one        | 99 988  | 100.0%    | 0.0%      | 16 756 620 | 167.6        |
| best_price        | 100 000 | 100.0%    | 0.0%      | 21 058 950 | 210.6        |
| random_price      | 100 000 | 100.0%    | 0.0%      | 18 417 270 | 184.2        |
| best_velocity     | 100 000 | 100.0%    | 0.0%      | 17 235 170 | 172.4        |
| random_velocity   | 100 000 | 100.0%    | 0.0%      | 16 909 960 | 169.1        |
| best_heuristics   | 100 000 | 100.0%    | 0.0%      | 19 235 130 | 192.4        |
| random_heuristics | 100 000 | 100.0%    | 0.0%      | 18 518 850 | 185.2        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 96 012     | 100 000    | 99 606     | 99 200     |
| Fill rate | 96.0%      | 100.0%     | 99.6%      | 99.2%      |
| Revenue   | 16 144 390 | 20 932 310 | 19 164 555 | 19 065 307 |

> Distribution of impressions: 3 988 (4.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 95 955     | 100 000    | 99 636     | 99 266     |
| Fill rate | 96.0%      | 100.0%     | 99.6%      | 99.3%      |
| Revenue   | 15 358 300 | 20 727 640 | 19 102 990 | 18 947 721 |

> Distribution of impressions: 4 045 (4.1% from average)

#### Advertising displays (impressions (disposal volume))

| Ad       | Volume | best_one      | random_one    | best_price    | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ---------------- | ------ | ------------- | ------------- | ------------- | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 13 208 | 13 208 (100%) | 6 631 (50%)   | 13 208 (100%) | 10 168 (77%) | 7 824 (59%)   | 7 041 (53%)     | 11 209 (85%)    | 10 604 (80%)      | 10 780 (82%)           | 10 891 (82%)   |
| Telecom_d46ed517452394a2 | 19 019 | 19 019 (100%) | 12 930 (68%)  | 19 019 (100%) | 12 918 (68%) | 11 266 (59%)  | 12 530 (66%)    | 12 721 (67%)    | 13 161 (69%)      | 13 068 (69%)           | 13 180 (69%)   |
| Retail_59c52779836b2bae | 15 257 | 15 257 (100%) | 9 297 (61%)   | 3 187 (21%)   | 8 552 (56%)  | 9 037 (59%)   | 9 299 (61%)     | 8 658 (57%)     | 8 658 (57%)       | 8 672 (57%)            | 8 717 (57%)    |
| Campaign_51288482374d537c | 5 474  | 5 474 (100%)  | 2 787 (51%)   | 0 (0%)        | 1 940 (35%)  | 3 243 (59%)   | 3 037 (55%)     | 1 177 (22%)     | 1 986 (36%)       | 836 (15%)              | 720 (13%)      |
| Automotive_9e1edff89ac9a790 | 8 025  | 8 025 (100%)  | 4 789 (60%)   | 8 025 (100%)  | 6 486 (81%)  | 4 754 (59%)   | 4 837 (60%)     | 6 513 (81%)     | 6 377 (79%)       | 6 459 (80%)            | 6 081 (76%)    |
| Campaign_4d4dc901c2e49788 | 14 773 | 14 773 (100%) | 9 394 (64%)   | 14 773 (100%) | 10 870 (74%) | 8 750 (59%)   | 9 533 (65%)     | 10 859 (74%)    | 10 675 (72%)      | 11 908 (81%)           | 11 027 (75%)   |
| Property_5a34d256a53751c3 | 9 028  | 7 160 (79%)   | 4 002 (44%)   | 9 028 (100%)  | 6 703 (74%)  | 5 347 (59%)   | 4 392 (49%)     | 7 699 (85%)     | 6 790 (75%)       | 7 363 (82%)            | 7 138 (79%)    |
| Retail_5d131e8ff2fd6390 | 8 351  | 6 671 (80%)   | 4 988 (60%)   | 428 (5%)      | 4 456 (53%)  | 4 947 (59%)   | 5 026 (60%)     | 3 813 (46%)     | 4 138 (50%)       | 4 087 (49%)            | 4 197 (50%)    |
| Health_0676356d6ba137b6 | 12 100 | 6 762 (56%)   | 12 100 (100%) | 8 036 (66%)   | 10 892 (90%) | 7 168 (59%)   | 10 082 (83%)    | 7 215 (60%)     | 9 341 (77%)       | 9 383 (78%)            | 9 230 (76%)    |
| Travel_3724963d1920e16a | 3 317  | 343 (10%)     | 1 548 (47%)   | 3 317 (100%)  | 1 846 (56%)  | 1 965 (59%)   | 1 651 (50%)     | 2 313 (70%)     | 1 851 (56%)       | 2 276 (69%)            | 2 254 (68%)    |
| Bank_93461467de106ae8 | 4 333  | 0 (0%)        | 1 651 (38%)   | 4 333 (100%)  | 1 734 (40%)  | 2 567 (59%)   | 1 888 (44%)     | 3 185 (74%)     | 2 076 (48%)       | 2 758 (64%)            | 2 811 (65%)    |
| Retail_6162b5875d2e4e9b | 3 211  | 762 (24%)     | 1 793 (56%)   | 1 330 (41%)   | 1 869 (58%)  | 1 902 (59%)   | 1 868 (58%)     | 1 996 (62%)     | 1 881 (59%)       | 1 978 (62%)            | 1 953 (61%)    |
| Retail_8846b13f4335d7b7 | 2 890  | 546 (19%)     | 1 617 (56%)   | 72 (2%)       | 1 239 (43%)  | 1 712 (59%)   | 1 637 (57%)     | 1 034 (36%)     | 1 214 (42%)       | 880 (30%)              | 1 010 (35%)    |
| Campaign_a54822eb2c43abe7 | 8 316  | 346 (4%)      | 4 706 (57%)   | 0 (0%)        | 2 491 (30%)  | 4 926 (59%)   | 4 890 (59%)     | 971 (12%)       | 2 696 (32%)       | 1 247 (15%)            | 1 354 (16%)    |
| Campaign_04055ec242bc0613 | 2 375  | 194 (8%)      | 1 405 (59%)   | 0 (0%)        | 991 (42%)    | 1 407 (59%)   | 1 397 (59%)     | 697 (29%)       | 958 (40%)         | 501 (21%)              | 621 (26%)      |
| Property_db25972d5f786d2e | 6 340  | 288 (5%)      | 2 879 (45%)   | 0 (0%)        | 1 838 (29%)  | 3 755 (59%)   | 3 141 (50%)     | 3 140 (50%)     | 2 152 (34%)       | 1 937 (31%)            | 2 025 (32%)    |
| Children_90daa9b022baf620 | 6 635  | 0 (0%)        | 3 510 (53%)   | 0 (0%)        | 2 226 (34%)  | 3 931 (59%)   | 3 631 (55%)     | 1 948 (29%)     | 2 294 (35%)       | 1 510 (23%)            | 1 448 (22%)    |
| Travel_a0a6420a0d37809f | 10 080 | 0 (0%)        | 4 487 (45%)   | 8 815 (87%)   | 4 206 (42%)  | 5 971 (59%)   | 4 773 (47%)     | 6 490 (64%)     | 4 586 (45%)       | 5 900 (59%)            | 6 356 (63%)    |
| Bank_fbe065970201fb55 | 6 186  | 0 (0%)        | 2 582 (42%)   | 6 186 (100%)  | 3 283 (53%)  | 3 664 (59%)   | 2 879 (47%)     | 4 821 (78%)     | 3 627 (59%)       | 4 433 (72%)            | 4 467 (72%)    |
| Campaign_d5e7563f29a5b384 | 9 899  | 1 172 (12%)   | 6 892 (70%)   | 243 (2%)      | 5 292 (53%)  | 5 864 (59%)   | 6 468 (65%)     | 3 541 (36%)     | 4 935 (50%)       | 3 216 (32%)            | 3 776 (38%)    |


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.8%, revenue -9.5%
- **A3 vs best_price**: impressions -0.7%, revenue -10.0%
- **A2 stability**: high (4.0% scatter)
- **A3 stability**: high (4.1% scatter)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 18 Scenario : Company 20, 100K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 20 |
| Requests | 100 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 2 302 174 impressions |
| Total budget (A3) | 396 788 820 units. |
| Mean CPM | 165.5 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 180 120     | 50 433 600  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 259 350     | 41 496 000  |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 208 050     | 29 127 000  |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 74 654      | 6 718 860   |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 109 440     | 27 360 000  |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 201 450     | 40 290 000  |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 123 120     | 39 398 400  |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 113 880     | 14 804 400  |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 165 000     | 24 750 000  |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 45 240      | 9 048 000   |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 59 097      | 11 819 400  |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 43 799      | 7 007 840   |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 39 419      | 4 336 090   |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 113 400     | 9 072 000   |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 32 399      | 3 239 900   |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 86 457      | 10 374 840  |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 90 480      | 9 048 000   |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 137 460     | 23 368 200  |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 84 360      | 20 246 400  |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 134 999     | 14 849 890  |

#### Classical Strategies (1 run)

| Strategy         | Impressions  | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------- | --------- | --------- | ---------- | ------------ |
| best_one          | 100 000 | 100.0%    | 0.0%      | 23 460 470 | 234.6        |
| random_one        | 100 000 | 100.0%    | 0.0%      | 16 756 700 | 167.6        |
| best_price        | 100 000 | 100.0%    | 0.0%      | 25 824 130 | 258.2        |
| random_price      | 100 000 | 100.0%    | 0.0%      | 18 417 270 | 184.2        |
| best_velocity     | 100 000 | 100.0%    | 0.0%      | 17 235 170 | 172.4        |
| random_velocity   | 100 000 | 100.0%    | 0.0%      | 16 758 420 | 167.6        |
| best_heuristics   | 100 000 | 100.0%    | 0.0%      | 25 233 330 | 252.3        |
| random_heuristics | 100 000 | 100.0%    | 0.0%      | 19 063 650 | 190.6        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 100 000    | 100 000    | 100 000    | 100 000    |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 14 566 640 | 25 814 540 | 23 450 085 | 22 982 537 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 100 000    | 100 000    | 100 000    | 100 000    |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 16 045 430 | 25 814 540 | 23 264 185 | 22 765 816 |

> Distribution of impressions: 0 (0.0% from average)

#### Advertising displays (impressions (disposal volume))

| Ad       | Volume  | best_one     | random_one  | best_price   | random_price | best_velocity | random_velocity | best_heuristics | random_heuristics | a2_single_valued (Wed.) | a3_small (Wed.) |
| ---------------- | ------- | ------------ | ----------- | ------------ | ------------ | ------------- | --------------- | --------------- | ----------------- | ---------------------- | -------------- |
| Bank_24d40196bd94b649 | 180 120 | 60 010 (33%) | 6 626 (4%)  | 19 228 (11%) | 10 168 (6%)  | 7 823 (4%)    | 6 603 (4%)      | 33 998 (19%)    | 12 475 (7%)       | 21 992 (12%)           | 20 973 (12%)   |
| Telecom_d46ed517452394a2 | 259 350 | 29 483 (11%) | 12 921 (5%) | 20 605 (8%)  | 12 918 (5%)  | 11 265 (4%)   | 12 931 (5%)     | 20 605 (8%)     | 13 865 (5%)       | 12 121 (5%)            | 12 887 (5%)    |
| Retail_59c52779836b2bae | 208 050 | 0 (0%)       | 9 295 (4%)  | 0 (0%)       | 8 552 (4%)   | 9 037 (4%)    | 9 267 (4%)      | 0 (0%)          | 8 239 (4%)        | 5 752 (3%)             | 5 459 (3%)     |
| Campaign_51288482374d537c | 74 654  | 0 (0%)       | 2 788 (4%)  | 0 (0%)       | 1 940 (3%)   | 3 243 (4%)    | 2 935 (4%)      | 0 (0%)          | 1 675 (2%)        | 194 (0%)               | 163 (0%)       |
| Automotive_9e1edff89ac9a790 | 109 440 | 357 (0%)     | 4 780 (4%)  | 7 673 (7%)   | 6 486 (6%)   | 4 754 (4%)    | 4 754 (4%)      | 7 673 (7%)      | 7 252 (7%)        | 11 225 (10%)           | 10 256 (9%)    |
| Campaign_4d4dc901c2e49788 | 201 450 | 7 065 (4%)   | 9 391 (5%)  | 7 065 (4%)   | 10 870 (5%)  | 8 750 (4%)    | 9 550 (5%)      | 7 065 (4%)      | 11 037 (5%)       | 10 849 (5%)            | 9 608 (5%)     |
| Property_5a34d256a53751c3 | 123 120 | 0 (0%)       | 4 002 (3%)  | 40 782 (33%) | 6 703 (5%)   | 5 348 (4%)    | 4 020 (3%)      | 26 012 (21%)    | 7 476 (6%)        | 18 441 (15%)           | 18 412 (15%)   |
| Retail_5d131e8ff2fd6390 | 113 880 | 720 (1%)     | 4 983 (4%)  | 421 (0%)     | 4 456 (4%)   | 4 947 (4%)    | 5 009 (4%)      | 421 (0%)        | 3 793 (3%)        | 2 386 (2%)             | 2 614 (2%)     |
| Health_0676356d6ba137b6 | 165 000 | 2 027 (1%)   | 12 150 (7%) | 2 098 (1%)   | 10 892 (7%)  | 7 167 (4%)    | 12 059 (7%)     | 2 098 (1%)      | 10 047 (6%)       | 6 873 (4%)             | 6 660 (4%)     |
| Travel_3724963d1920e16a | 45 240  | 0 (0%)       | 1 549 (3%)  | 1 636 (4%)   | 1 846 (4%)   | 1 965 (4%)    | 1 524 (3%)      | 1 636 (4%)      | 1 691 (4%)        | 1 986 (4%)             | 2 401 (5%)     |
| Bank_93461467de106ae8 | 59 097  | 0 (0%)       | 1 647 (3%)  | 0 (0%)       | 1 734 (3%)   | 2 567 (4%)    | 1 675 (3%)      | 0 (0%)          | 1 729 (3%)        | 829 (1%)               | 806 (1%)       |
| Retail_6162b5875d2e4e9b | 43 799  | 71 (0%)      | 1 796 (4%)  | 225 (1%)     | 1 869 (4%)   | 1 903 (4%)    | 1 786 (4%)      | 225 (1%)        | 1 778 (4%)        | 2 011 (5%)             | 1 995 (5%)     |
| Retail_8846b13f4335d7b7 | 39 419  | 64 (0%)      | 1 615 (4%)  | 64 (0%)      | 1 239 (3%)   | 1 713 (4%)    | 1 611 (4%)      | 57 (0%)         | 1 020 (3%)        | 280 (1%)               | 400 (1%)       |
| Campaign_a54822eb2c43abe7 | 113 400 | 0 (0%)       | 4 708 (4%)  | 0 (0%)       | 2 491 (2%)   | 4 926 (4%)    | 4 774 (4%)      | 0 (0%)          | 2 054 (2%)        | 97 (0%)                | 186 (0%)       |
| Campaign_04055ec242bc0613 | 32 399  | 24 (0%)      | 1 406 (4%)  | 0 (0%)       | 991 (3%)     | 1 408 (4%)    | 1 405 (4%)      | 0 (0%)          | 861 (3%)          | 131 (0%)               | 210 (1%)       |
| Property_db25972d5f786d2e | 86 457  | 0 (0%)       | 2 884 (3%)  | 0 (0%)       | 1 838 (2%)   | 3 755 (4%)    | 2 893 (3%)      | 0 (0%)          | 1 547 (2%)        | 9 (0%)                 | 16 (0%)        |
| Children_90daa9b022baf620 | 90 480  | 0 (0%)       | 3 501 (4%)  | 0 (0%)       | 2 226 (2%)   | 3 930 (4%)    | 3 427 (4%)      | 0 (0%)          | 1 834 (2%)        | 175 (0%)               | 203 (0%)       |
| Travel_a0a6420a0d37809f | 137 460 | 0 (0%)       | 4 484 (3%)  | 0 (0%)       | 4 206 (3%)   | 5 971 (4%)    | 4 408 (3%)      | 0 (0%)          | 3 804 (3%)        | 594 (0%)               | 1 727 (1%)     |
| Bank_fbe065970201fb55 | 84 360  | 0 (0%)       | 2 582 (3%)  | 0 (0%)       | 3 283 (4%)   | 3 664 (4%)    | 2 609 (3%)      | 0 (0%)          | 3 291 (4%)        | 2 630 (3%)             | 3 282 (4%)     |
| Campaign_d5e7563f29a5b384 | 134 999 | 179 (0%)     | 6 892 (5%)  | 203 (0%)     | 5 292 (4%)   | 5 864 (4%)    | 6 760 (5%)      | 210 (0%)        | 4 532 (3%)        | 1 417 (1%)             | 1 731 (1%)     |


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -11.0%
- **A3 vs best_price**: impressions +0.0%, revenue -11.8%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
## 19 Scenario: Company 100, 10K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 100 |
| Requests | 10 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 105 770 impressions |
| Total budget (A3) | 16 182 487 units. |
| Mean CPM | 149.8 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 4 202       | 1 176 560   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 6 051       | 968 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 4 854       | 679 560     |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 1 741       | 156 690     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 2 553       | 638 250     |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 4 700       | 940 000     |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 2 872       | 919 040     |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 2 657       | 345 410     |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 3 849       | 577 350     |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 1 055       | 211 000     |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 1 378       | 275 600     |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 1 021       | 163 360     |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 919         | 101 090     |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 2 646       | 211 680     |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 755         | 75 500      |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 2 017       | 242 040     |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 2 111       | 211 100     |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 3 207       | 545 190     |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 1 968       | 472 320     |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 3 150       | 346 500     |
| Bank_5604b370baee11e8 | 19.0%      | 300 | 4.5       | 1 330       | 399 000     |
| Retail_4765ba374f6aecc1 | 27.0%      | 130 | 3.5       | 1 890       | 245 700     |
| Telecom_ed706ab0d06977cd | 14.0%      | 140 | 3.5       | 980         | 137 200     |
| Retail_c08a2c8e2aaba579 | 23.0%      | 100 | 3.0       | 1 610       | 161 000     |
| Campaign_7dc611819a260eaf | 15.0%      | 110 | 3.0       | 1 050       | 115 500     |
| Campaign_0ec7f92f18e461bb | 10.5%      | 80  | 2.5       | 735         | 58 800      |
| Campaign_9d1008b88789df38 | 11.9%      | 280 | 4.0       | 834         | 233 520     |
| Campaign_0cc18fd853a12790 | 11.2%      | 400 | 5.0       | 781         | 312 400     |
| Health_6443f22d5852d528 | 43.5%      | 160 | 3.5       | 3 041       | 486 560     |
| Campaign_9b4d1a7d25db93e0 | 45.8%      | 90  | 3.0       | 3 207       | 288 630     |
| Bank_412b1a6e792a6b27 | 19.0%      | 150 | 4.0       | 1 330       | 199 500     |
| Retail_8a95d706a952fc0a | 11.4%      | 92  | 3.1       | 798         | 73 177      |
| Campaign_25d7a2ecf9a34029 | 21.5%      | 127 | 3.7       | 1 502       | 190 303     |
| Campaign_320311c675dff6d8 | 2.6%       | 100 | 2.8       | 184         | 18 400      |
| Retail_1f18939ad657c07d | 3.3%       | 137 | 3.4       | 229         | 31 304      |
| Automotive_0386a6443f12a5ec | 1.1%       | 263 | 4.0       | 75          | 19 748      |
| Campaign_d4727b5c19a92dfe | 10.5%      | 120 | 3.1       | 735         | 88 200      |
| Bank_c99262d85fa8290e | 6.1%       | 150 | 4.2       | 425         | 63 750      |
| Retail_fd2940988420c92e | 5.7%       | 92  | 3.3       | 399         | 36 588      |
| Campaign_6f7317281c63b409 | 2.9%       | 127 | 3.9       | 203         | 25 720      |
| Campaign_93291ba17bc56b3d | 6.0%       | 100 | 2.5       | 420         | 42 000      |
| Retail_c62ca80310d8e264 | 2.8%       | 137 | 3.1       | 196         | 26 793      |
| Automotive_e8c4f8cb60890542 | 2.7%       | 263 | 4.2       | 186         | 48 974      |
| Campaign_3995407d5cd6a644 | 7.7%       | 120 | 3.3       | 539         | 64 680      |
| Bank_b9c2207a5f26e683 | 10.6%      | 150 | 4.4       | 744         | 111 600     |
| Retail_8ce549b38a2441de | 14.3%      | 92  | 3.0       | 997         | 91 425      |
| Campaign_f5af87d0012d3fe4 | 8.7%       | 127 | 3.6       | 609         | 77 160      |
| Campaign_ac250cdeb965d918 | 1.9%       | 100 | 2.7       | 134         | 13 400      |
| Retail_2c64438c3bb04f75 | 1.4%       | 137 | 3.3       | 98          | 13 397      |
| Automotive_878a8e7c40af35fd | 0.4%       | 263 | 4.4       | 25          | 6 582       |
| Campaign_96b37a70e8bdba6c | 17.5%      | 120 | 3.0       | 1 225       | 147 000     |
| Bank_d4ac740fdbbfe6b0 | 9.1%       | 150 | 4.1       | 638         | 95 700      |
| Retail_d5a9402ae3c29c35 | 35.1%      | 92  | 3.2       | 2 460       | 225 582     |
| Campaign_1745b225a2e0be46 | 6.4%       | 127 | 3.8       | 446         | 56 508      |
| Campaign_c36fd267e3128ae2 | 3.4%       | 100 | 2.9       | 235         | 23 500      |
| Retail_5be29648bbf06d3f | 3.5%       | 137 | 3.0       | 245         | 33 492      |
| Automotive_6ac00073f2474735 | 1.1%       | 263 | 4.1       | 75          | 19 748      |
| Campaign_c4fe2cd3875e7055 | 5.6%       | 120 | 3.2       | 391         | 46 920      |
| Bank_d4d4acde026fc4a8 | 4.6%       | 150 | 4.3       | 319         | 47 850      |
| Retail_0390e1bd6c0c7aa8 | 4.8%       | 92  | 3.4       | 332         | 30 444      |
| Campaign_c74dce135eae7c52 | 14.5%      | 127 | 3.5       | 1 015       | 128 600     |
| Campaign_59fdd82d61a7f646 | 2.9%       | 100 | 2.6       | 201         | 20 100      |
| Retail_694c6720f451703a | 8.7%       | 137 | 3.2       | 606         | 82 840      |
| Automotive_a299e1a2466e6aeb | 0.8%       | 263 | 4.3       | 55          | 14 482      |
| Campaign_4706c393b25fb3f0 | 9.8%       | 120 | 3.4       | 686         | 82 320      |
| Bank_435aedebb1bf7a2d | 11.4%      | 150 | 4.0       | 798         | 119 700     |
| Retail_53e8d88f3a226e00 | 14.2%      | 92  | 3.1       | 997         | 91 425      |
| Campaign_f9273b882fb2cc0c | 4.6%       | 127 | 3.7       | 324         | 41 051      |
| Campaign_ae23878b7e8a0ec1 | 1.4%       | 100 | 2.8       | 100         | 10 000      |
| Retail_06f2cf00d35adbca | 1.2%       | 137 | 3.4       | 81          | 11 073      |
| Automotive_f4f5b93b3116fba3 | 1.8%       | 263 | 4.0       | 126         | 33 176      |
| Campaign_089e705cd41af878 | 8.4%       | 120 | 3.1       | 587         | 70 440      |
| Bank_31ea3c607fa2ed52 | 28.1%      | 150 | 4.2       | 1 968       | 295 200     |
| Retail_cbef4c4fbb517dd1 | 10.4%      | 92  | 3.3       | 731         | 67 033      |
| Campaign_4c3aa0fbe837f21f | 8.1%       | 127 | 3.9       | 568         | 71 966      |
| Campaign_ea02a7e77d42a558 | 3.6%       | 100 | 2.5       | 252         | 25 200      |
| Retail_ba29207cfea4b3f6 | 3.5%       | 137 | 3.1       | 245         | 33 492      |
| Automotive_cef55d2ad4127179 | 0.6%       | 263 | 4.2       | 40          | 10 532      |
| Campaign_95afde8bce1ca2fd | 4.2%       | 120 | 3.3       | 293         | 35 160      |
| Bank_8de7e73806d62f7f | 3.8%       | 150 | 4.4       | 266         | 39 900      |
| Retail_9d523ac2afb377fc | 23.8%      | 92  | 3.0       | 1 662       | 152 405     |
| Campaign_d8646f2deca6903a | 7.0%       | 127 | 3.6       | 487         | 61 703      |
| Campaign_2bd323ca0951e219 | 8.9%       | 100 | 2.7       | 621         | 62 100      |
| Retail_3f81958b91b44b57 | 2.6%       | 137 | 3.3       | 180         | 24 606      |
| Automotive_6d602705b3344057 | 1.0%       | 263 | 4.4       | 70          | 18 431      |
| Campaign_745dba57acaf7918 | 10.5%      | 120 | 3.0       | 735         | 88 200      |
| Bank_0abaaf432ed16231 | 11.4%      | 150 | 4.1       | 798         | 119 700     |
| Retail_0fde75a9a148a512 | 7.6%       | 92  | 3.2       | 532         | 48 784      |
| Campaign_a90aa3ddd1a54bbc | 3.5%       | 127 | 3.8       | 243         | 30 788      |
| Campaign_40e1d170d51e276f | 1.2%       | 100 | 2.9       | 84          | 8 400       |
| Retail_ee5b98dcb1e20583 | 5.8%       | 137 | 3.0       | 409         | 55 910      |
| Automotive_3f50906f88bf8469 | 0.9%       | 263 | 4.1       | 60          | 15 798      |
| Campaign_b4381361bcb690b9 | 25.9%      | 120 | 3.2       | 1 812       | 217 440     |
| Bank_c142b51224633f3a | 8.4%       | 150 | 4.3       | 585         | 87 750      |
| Retail_48fb5a3bfa1a566c | 13.3%      | 92  | 3.4       | 930         | 85 281      |
| Campaign_ec0134764fd02d46 | 8.7%       | 127 | 3.5       | 609         | 77 160      |
| Campaign_3c4832e7fc1e1e90 | 3.6%       | 100 | 2.6       | 251         | 25 100      |
| Retail_f01b7bcd1d812f00 | 1.9%       | 137 | 3.2       | 131         | 17 908      |
| Automotive_4f12f5c2a0f07630 | 0.4%       | 263 | 4.3       | 30          | 7 899       |
| Campaign_afd3cf7367db1093 | 3.5%       | 120 | 3.4       | 244         | 29 280      |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 10 000 | 100.0%    | 0.0%      | 2 135 890 | 213.6        |
| random_one        | 10 000 | 100.0%    | 0.0%      | 1 475 165 | 147.5        |
| best_price        | 10 000 | 100.0%    | 0.0%      | 2 655 572 | 265.6        |
| random_price      | 10 000 | 100.0%    | 0.0%      | 1 675 364 | 167.5        |
| best_velocity     | 10 000 | 100.0%    | 0.0%      | 1 530 167 | 153.0        |
| random_velocity   | 10 000 | 100.0%    | 0.0%      | 1 476 880 | 147.7        |
| best_heuristics   | 10 000 | 100.0%    | 0.0%      | 2 526 485 | 252.6        |
| random_heuristics | 10 000 | 100.0%    | 0.0%      | 1 740 824 | 174.1        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 10 000    | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 818 590 | 2 635 418 | 2 367 479 | 2 336 979 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 10 000    | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 716 518 | 2 635 913 | 2 360 846 | 2 332 530 |

> Distribution of impressions: 0 (0.0% from average)


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -12.0%
- **A3 vs best_price**: impressions +0.0%, revenue -12.2%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)

---
## 20 Scenario: Company 100, 10K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 100 |
| Requests | 10 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 33 212 impressions |
| Total budget (A3) | 5 081 097 units. |
| Mean CPM | 149.8 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 1 320       | 369 600     |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 1 901       | 304 160     |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 1 525       | 213 500     |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 547         | 49 230      |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 802         | 200 500     |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 1 477       | 295 400     |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 902         | 288 640     |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 835         | 108 550     |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 1 210       | 181 500     |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 331         | 66 200      |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 433         | 86 600      |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 321         | 51 360      |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 289         | 31 790      |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 831         | 66 480      |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 237         | 23 700      |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 634         | 76 080      |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 663         | 66 300      |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 1 008       | 171 360     |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 618         | 148 320     |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 990         | 108 900     |
| Bank_5604b370baee11e8 | 19.0%      | 300 | 4.5       | 418         | 125 400     |
| Retail_4765ba374f6aecc1 | 27.0%      | 130 | 3.5       | 594         | 77 220      |
| Telecom_ed706ab0d06977cd | 14.0%      | 140 | 3.5       | 308         | 43 120      |
| Retail_c08a2c8e2aaba579 | 23.0%      | 100 | 3.0       | 506         | 50 600      |
| Campaign_7dc611819a260eaf | 15.0%      | 110 | 3.0       | 330         | 36 300      |
| Campaign_0ec7f92f18e461bb | 10.5%      | 80  | 2.5       | 231         | 18 480      |
| Campaign_9d1008b88789df38 | 11.9%      | 280 | 4.0       | 262         | 73 360      |
| Campaign_0cc18fd853a12790 | 11.2%      | 400 | 5.0       | 245         | 98 000      |
| Health_6443f22d5852d528 | 43.5%      | 160 | 3.5       | 955         | 152 800     |
| Campaign_9b4d1a7d25db93e0 | 45.8%      | 90  | 3.0       | 1 008       | 90 720      |
| Bank_412b1a6e792a6b27 | 19.0%      | 150 | 4.0       | 418         | 62 700      |
| Retail_8a95d706a952fc0a | 11.4%      | 92  | 3.1       | 250         | 22 925      |
| Campaign_25d7a2ecf9a34029 | 21.5%      | 127 | 3.7       | 472         | 59 802      |
| Campaign_320311c675dff6d8 | 2.6%       | 100 | 2.8       | 58          | 5 800       |
| Retail_1f18939ad657c07d | 3.3%       | 137 | 3.4       | 72          | 9 842       |
| Automotive_0386a6443f12a5ec | 1.1%       | 263 | 4.0       | 23          | 6 056       |
| Campaign_d4727b5c19a92dfe | 10.5%      | 120 | 3.1       | 231         | 27 720      |
| Bank_c99262d85fa8290e | 6.1%       | 150 | 4.2       | 133         | 19 950      |
| Retail_fd2940988420c92e | 5.7%       | 92  | 3.3       | 125         | 11 462      |
| Campaign_6f7317281c63b409 | 2.9%       | 127 | 3.9       | 63          | 7 982       |
| Campaign_93291ba17bc56b3d | 6.0%       | 100 | 2.5       | 132         | 13 200      |
| Retail_c62ca80310d8e264 | 2.8%       | 137 | 3.1       | 61          | 8 339       |
| Automotive_e8c4f8cb60890542 | 2.7%       | 263 | 4.2       | 58          | 15 271      |
| Campaign_3995407d5cd6a644 | 7.7%       | 120 | 3.3       | 169         | 20 280      |
| Bank_b9c2207a5f26e683 | 10.6%      | 150 | 4.4       | 234         | 35 100      |
| Retail_8ce549b38a2441de | 14.3%      | 92  | 3.0       | 313         | 28 702      |
| Campaign_f5af87d0012d3fe4 | 8.7%       | 127 | 3.6       | 191         | 24 200      |
| Campaign_ac250cdeb965d918 | 1.9%       | 100 | 2.7       | 42          | 4 200       |
| Retail_2c64438c3bb04f75 | 1.4%       | 137 | 3.3       | 30          | 4 101       |
| Automotive_878a8e7c40af35fd | 0.4%       | 263 | 4.4       | 7           | 1 843       |
| Campaign_96b37a70e8bdba6c | 17.5%      | 120 | 3.0       | 385         | 46 200      |
| Bank_d4ac740fdbbfe6b0 | 9.1%       | 150 | 4.1       | 200         | 30 000      |
| Retail_d5a9402ae3c29c35 | 35.1%      | 92  | 3.2       | 773         | 70 884      |
| Campaign_1745b225a2e0be46 | 6.4%       | 127 | 3.8       | 140         | 17 738      |
| Campaign_c36fd267e3128ae2 | 3.4%       | 100 | 2.9       | 73          | 7 300       |
| Retail_5be29648bbf06d3f | 3.5%       | 137 | 3.0       | 77          | 10 526      |
| Automotive_6ac00073f2474735 | 1.1%       | 263 | 4.1       | 23          | 6 056       |
| Campaign_c4fe2cd3875e7055 | 5.6%       | 120 | 3.2       | 123         | 14 760      |
| Bank_d4d4acde026fc4a8 | 4.6%       | 150 | 4.3       | 100         | 15 000      |
| Retail_0390e1bd6c0c7aa8 | 4.8%       | 92  | 3.4       | 104         | 9 537       |
| Campaign_c74dce135eae7c52 | 14.5%      | 127 | 3.5       | 319         | 40 417      |
| Campaign_59fdd82d61a7f646 | 2.9%       | 100 | 2.6       | 63          | 6 300       |
| Retail_694c6720f451703a | 8.7%       | 137 | 3.2       | 190         | 25 973      |
| Automotive_a299e1a2466e6aeb | 0.8%       | 263 | 4.3       | 17          | 4 476       |
| Campaign_4706c393b25fb3f0 | 9.8%       | 120 | 3.4       | 215         | 25 800      |
| Bank_435aedebb1bf7a2d | 11.4%      | 150 | 4.0       | 250         | 37 500      |
| Retail_53e8d88f3a226e00 | 14.2%      | 92  | 3.1       | 313         | 28 702      |
| Campaign_f9273b882fb2cc0c | 4.6%       | 127 | 3.7       | 102         | 12 923      |
| Campaign_ae23878b7e8a0ec1 | 1.4%       | 100 | 2.8       | 31          | 3 100       |
| Retail_06f2cf00d35adbca | 1.2%       | 137 | 3.4       | 25          | 3 417       |
| Automotive_f4f5b93b3116fba3 | 1.8%       | 263 | 4.0       | 39          | 10 269      |
| Campaign_089e705cd41af878 | 8.4%       | 120 | 3.1       | 184         | 22 080      |
| Bank_31ea3c607fa2ed52 | 28.1%      | 150 | 4.2       | 618         | 92 700      |
| Retail_cbef4c4fbb517dd1 | 10.4%      | 92  | 3.3       | 229         | 20 999      |
| Campaign_4c3aa0fbe837f21f | 8.1%       | 127 | 3.9       | 178         | 22 553      |
| Campaign_ea02a7e77d42a558 | 3.6%       | 100 | 2.5       | 79          | 7 900       |
| Retail_ba29207cfea4b3f6 | 3.5%       | 137 | 3.1       | 77          | 10 526      |
| Automotive_cef55d2ad4127179 | 0.6%       | 263 | 4.2       | 12          | 3 160       |
| Campaign_95afde8bce1ca2fd | 4.2%       | 120 | 3.3       | 92          | 11 040      |
| Bank_8de7e73806d62f7f | 3.8%       | 150 | 4.4       | 83          | 12 450      |
| Retail_9d523ac2afb377fc | 23.8%      | 92  | 3.0       | 522         | 47 867      |
| Campaign_d8646f2deca6903a | 7.0%       | 127 | 3.6       | 153         | 19 385      |
| Campaign_2bd323ca0951e219 | 8.9%       | 100 | 2.7       | 195         | 19 500      |
| Retail_3f81958b91b44b57 | 2.6%       | 137 | 3.3       | 56          | 7 655       |
| Automotive_6d602705b3344057 | 1.0%       | 263 | 4.4       | 22          | 5 793       |
| Campaign_745dba57acaf7918 | 10.5%      | 120 | 3.0       | 231         | 27 720      |
| Bank_0abaaf432ed16231 | 11.4%      | 150 | 4.1       | 250         | 37 500      |
| Retail_0fde75a9a148a512 | 7.6%       | 92  | 3.2       | 167         | 15 314      |
| Campaign_a90aa3ddd1a54bbc | 3.5%       | 127 | 3.8       | 76          | 9 629       |
| Campaign_40e1d170d51e276f | 1.2%       | 100 | 2.9       | 26          | 2 600       |
| Retail_ee5b98dcb1e20583 | 5.8%       | 137 | 3.0       | 128         | 17 498      |
| Automotive_3f50906f88bf8469 | 0.9%       | 263 | 4.1       | 19          | 5 003       |
| Campaign_b4381361bcb690b9 | 25.9%      | 120 | 3.2       | 569         | 68 280      |
| Bank_c142b51224633f3a | 8.4%       | 150 | 4.3       | 183         | 27 450      |
| Retail_48fb5a3bfa1a566c | 13.3%      | 92  | 3.4       | 292         | 26 776      |
| Campaign_ec0134764fd02d46 | 8.7%       | 127 | 3.5       | 191         | 24 200      |
| Campaign_3c4832e7fc1e1e90 | 3.6%       | 100 | 2.6       | 79          | 7 900       |
| Retail_f01b7bcd1d812f00 | 1.9%       | 137 | 3.2       | 41          | 5 605       |
| Automotive_4f12f5c2a0f07630 | 0.4%       | 263 | 4.3       | 9           | 2 370       |
| Campaign_afd3cf7367db1093 | 3.5%       | 120 | 3.4       | 76          | 9 120       |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 10 000 | 100.0%    | 0.0%      | 1 886 650 | 188.7        |
| random_one        | 10 000 | 100.0%    | 0.0%      | 1 475 165 | 147.5        |
| best_price        | 10 000 | 100.0%    | 0.0%      | 2 275 807 | 227.6        |
| random_price      | 10 000 | 100.0%    | 0.0%      | 1 675 174 | 167.5        |
| best_velocity     | 10 000 | 100.0%    | 0.0%      | 1 529 960 | 153.0        |
| random_velocity   | 10 000 | 100.0%    | 0.0%      | 1 483 910 | 148.4        |
| best_heuristics   | 10 000 | 100.0%    | 0.0%      | 2 029 137 | 202.9        |
| random_heuristics | 10 000 | 100.0%    | 0.0%      | 1 710 862 | 171.1        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 997     | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 571 274 | 2 232 588 | 1 999 291 | 1 988 399 |

> Distribution of impressions: 3 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 9 997     | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 560 744 | 2 248 202 | 1 993 362 | 1 986 397 |

> Distribution of impressions: 3 (0.0% from average)


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.0%, revenue -12.6%
- **A3 vs best_price**: impressions -0.0%, revenue -12.7%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 21 Scenario : Company 100, 10K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 100 |
| Requests | 10 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 453 458 impressions |
| Total budget (A3) | 69 377 376 units. |
| Mean CPM | 149.8 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 18 012      | 5 043 360   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 25 935      | 4 149 600   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 20 805      | 2 912 700   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 7 465       | 671 850     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 10 944      | 2 736 000   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 20 145      | 4 029 000   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 12 312      | 3 939 840   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 11 388      | 1 480 440   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 16 500      | 2 475 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 4 524       | 904 800     |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 5 909       | 1 181 800   |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 4 380       | 700 800     |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 3 942       | 433 620     |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 11 340      | 907 200     |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 3 239       | 323 900     |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 8 645       | 1 037 400   |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 9 048       | 904 800     |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 13 746      | 2 336 820   |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 8 436       | 2 024 640   |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 13 500      | 1 485 000   |
| Bank_5604b370baee11e8 | 19.0%      | 300 | 4.5       | 5 700       | 1 710 000   |
| Retail_4765ba374f6aecc1 | 27.0%      | 130 | 3.5       | 8 103       | 1 053 390   |
| Telecom_ed706ab0d06977cd | 14.0%      | 140 | 3.5       | 4 200       | 588 000     |
| Retail_c08a2c8e2aaba579 | 23.0%      | 100 | 3.0       | 6 900       | 690 000     |
| Campaign_7dc611819a260eaf | 15.0%      | 110 | 3.0       | 4 500       | 495 000     |
| Campaign_0ec7f92f18e461bb | 10.5%      | 80  | 2.5       | 3 150       | 252 000     |
| Campaign_9d1008b88789df38 | 11.9%      | 280 | 4.0       | 3 576       | 1 001 280   |
| Campaign_0cc18fd853a12790 | 11.2%      | 400 | 5.0       | 3 347       | 1 338 800   |
| Health_6443f22d5852d528 | 43.5%      | 160 | 3.5       | 13 035      | 2 085 600   |
| Campaign_9b4d1a7d25db93e0 | 45.8%      | 90  | 3.0       | 13 746      | 1 237 140   |
| Bank_412b1a6e792a6b27 | 19.0%      | 150 | 4.0       | 5 700       | 855 000     |
| Retail_8a95d706a952fc0a | 11.4%      | 92  | 3.1       | 3 420       | 313 614     |
| Campaign_25d7a2ecf9a34029 | 21.5%      | 127 | 3.7       | 6 438       | 815 695     |
| Campaign_320311c675dff6d8 | 2.6%       | 100 | 2.8       | 792         | 79 200      |
| Retail_1f18939ad657c07d | 3.3%       | 137 | 3.4       | 982         | 134 239     |
| Automotive_0386a6443f12a5ec | 1.1%       | 263 | 4.0       | 324         | 85 309      |
| Campaign_d4727b5c19a92dfe | 10.5%      | 120 | 3.1       | 3 150       | 378 000     |
| Bank_c99262d85fa8290e | 6.1%       | 150 | 4.2       | 1 824       | 273 600     |
| Retail_fd2940988420c92e | 5.7%       | 92  | 3.3       | 1 710       | 156 807     |
| Campaign_6f7317281c63b409 | 2.9%       | 127 | 3.9       | 870         | 110 229     |
| Campaign_93291ba17bc56b3d | 6.0%       | 100 | 2.5       | 1 800       | 180 000     |
| Retail_c62ca80310d8e264 | 2.8%       | 137 | 3.1       | 842         | 115 101     |
| Automotive_e8c4f8cb60890542 | 2.7%       | 263 | 4.2       | 799         | 210 377     |
| Campaign_3995407d5cd6a644 | 7.7%       | 120 | 3.3       | 2 310       | 277 200     |
| Bank_b9c2207a5f26e683 | 10.6%      | 150 | 4.4       | 3 192       | 478 800     |
| Retail_8ce549b38a2441de | 14.3%      | 92  | 3.0       | 4 275       | 392 018     |
| Campaign_f5af87d0012d3fe4 | 8.7%       | 127 | 3.6       | 2 610       | 330 687     |
| Campaign_ac250cdeb965d918 | 1.9%       | 100 | 2.7       | 575         | 57 500      |
| Retail_2c64438c3bb04f75 | 1.4%       | 137 | 3.3       | 421         | 57 551      |
| Automotive_878a8e7c40af35fd | 0.4%       | 263 | 4.4       | 108         | 28 436      |
| Campaign_96b37a70e8bdba6c | 17.5%      | 120 | 3.0       | 5 250       | 630 000     |
| Bank_d4ac740fdbbfe6b0 | 9.1%       | 150 | 4.1       | 2 736       | 410 400     |
| Retail_d5a9402ae3c29c35 | 35.1%      | 92  | 3.2       | 10 545      | 966 976     |
| Campaign_1745b225a2e0be46 | 6.4%       | 127 | 3.8       | 1 914       | 242 504     |
| Campaign_c36fd267e3128ae2 | 3.4%       | 100 | 2.9       | 1 008       | 100 800     |
| Retail_5be29648bbf06d3f | 3.5%       | 137 | 3.0       | 1 053       | 143 945     |
| Automotive_6ac00073f2474735 | 1.1%       | 263 | 4.1       | 324         | 85 309      |
| Campaign_c4fe2cd3875e7055 | 5.6%       | 120 | 3.2       | 1 679       | 201 480     |
| Bank_d4d4acde026fc4a8 | 4.6%       | 150 | 4.3       | 1 368       | 205 200     |
| Retail_0390e1bd6c0c7aa8 | 4.8%       | 92  | 3.4       | 1 425       | 130 672     |
| Campaign_c74dce135eae7c52 | 14.5%      | 127 | 3.5       | 4 350       | 551 145     |
| Campaign_59fdd82d61a7f646 | 2.9%       | 100 | 2.6       | 864         | 86 400      |
| Retail_694c6720f451703a | 8.7%       | 137 | 3.2       | 2 597       | 355 010     |
| Automotive_a299e1a2466e6aeb | 0.8%       | 263 | 4.3       | 237         | 62 402      |
| Campaign_4706c393b25fb3f0 | 9.8%       | 120 | 3.4       | 2 940       | 352 800     |
| Bank_435aedebb1bf7a2d | 11.4%      | 150 | 4.0       | 3 420       | 513 000     |
| Retail_53e8d88f3a226e00 | 14.2%      | 92  | 3.1       | 4 274       | 391 926     |
| Campaign_f9273b882fb2cc0c | 4.6%       | 127 | 3.7       | 1 392       | 176 366     |
| Campaign_ae23878b7e8a0ec1 | 1.4%       | 100 | 2.8       | 432         | 43 200      |
| Retail_06f2cf00d35adbca | 1.2%       | 137 | 3.4       | 351         | 47 982      |
| Automotive_f4f5b93b3116fba3 | 1.8%       | 263 | 4.0       | 540         | 142 182     |
| Campaign_089e705cd41af878 | 8.4%       | 120 | 3.1       | 2 519       | 302 280     |
| Bank_31ea3c607fa2ed52 | 28.1%      | 150 | 4.2       | 8 436       | 1 265 400   |
| Retail_cbef4c4fbb517dd1 | 10.4%      | 92  | 3.3       | 3 135       | 287 480     |
| Campaign_4c3aa0fbe837f21f | 8.1%       | 127 | 3.9       | 2 436       | 308 641     |
| Campaign_ea02a7e77d42a558 | 3.6%       | 100 | 2.5       | 1 080       | 108 000     |
| Retail_ba29207cfea4b3f6 | 3.5%       | 137 | 3.1       | 1 053       | 143 945     |
| Automotive_cef55d2ad4127179 | 0.6%       | 263 | 4.2       | 172         | 45 288      |
| Campaign_95afde8bce1ca2fd | 4.2%       | 120 | 3.3       | 1 259       | 151 080     |
| Bank_8de7e73806d62f7f | 3.8%       | 150 | 4.4       | 1 140       | 171 000     |
| Retail_9d523ac2afb377fc | 23.8%      | 92  | 3.0       | 7 125       | 653 362     |
| Campaign_d8646f2deca6903a | 7.0%       | 127 | 3.6       | 2 088       | 264 550     |
| Campaign_2bd323ca0951e219 | 8.9%       | 100 | 2.7       | 2 663       | 266 300     |
| Retail_3f81958b91b44b57 | 2.6%       | 137 | 3.3       | 772         | 105 532     |
| Automotive_6d602705b3344057 | 1.0%       | 263 | 4.4       | 302         | 79 517      |
| Campaign_745dba57acaf7918 | 10.5%      | 120 | 3.0       | 3 150       | 378 000     |
| Bank_0abaaf432ed16231 | 11.4%      | 150 | 4.1       | 3 420       | 513 000     |
| Retail_0fde75a9a148a512 | 7.6%       | 92  | 3.2       | 2 280       | 209 076     |
| Campaign_a90aa3ddd1a54bbc | 3.5%       | 127 | 3.8       | 1 044       | 132 275     |
| Campaign_40e1d170d51e276f | 1.2%       | 100 | 2.9       | 360         | 36 000      |
| Retail_ee5b98dcb1e20583 | 5.8%       | 137 | 3.0       | 1 755       | 239 908     |
| Automotive_3f50906f88bf8469 | 0.9%       | 263 | 4.1       | 259         | 68 195      |
| Campaign_b4381361bcb690b9 | 25.9%      | 120 | 3.2       | 7 770       | 932 400     |
| Bank_c142b51224633f3a | 8.4%       | 150 | 4.3       | 2 508       | 376 200     |
| Retail_48fb5a3bfa1a566c | 13.3%      | 92  | 3.4       | 3 990       | 365 883     |
| Campaign_ec0134764fd02d46 | 8.7%       | 127 | 3.5       | 2 610       | 330 687     |
| Campaign_3c4832e7fc1e1e90 | 3.6%       | 100 | 2.6       | 1 080       | 108 000     |
| Retail_f01b7bcd1d812f00 | 1.9%       | 137 | 3.2       | 561         | 76 689      |
| Automotive_4f12f5c2a0f07630 | 0.4%       | 263 | 4.3       | 129         | 33 966      |
| Campaign_afd3cf7367db1093 | 3.5%       | 120 | 3.4       | 1 049       | 125 880     |

#### Classical Strategies (1 run)

| Strategy         | Impressions | Fill rate | Miss rate | Revenue   | Avg.CPM/display |
| ----------------- | ------ | --------- | --------- | --------- | ------------ |
| best_one          | 10 000 | 100.0%    | 0.0%      | 2 351 970 | 235.2        |
| random_one        | 10 000 | 100.0%    | 0.0%      | 1 475 165 | 147.5        |
| best_price        | 10 000 | 100.0%    | 0.0%      | 2 698 508 | 269.9        |
| random_price      | 10 000 | 100.0%    | 0.0%      | 1 675 364 | 167.5        |
| best_velocity     | 10 000 | 100.0%    | 0.0%      | 1 530 185 | 153.0        |
| random_velocity   | 10 000 | 100.0%    | 0.0%      | 1 475 928 | 147.6        |
| best_heuristics   | 10 000 | 100.0%    | 0.0%      | 2 661 904 | 266.2        |
| random_heuristics | 10 000 | 100.0%    | 0.0%      | 1 746 846 | 174.7        |

#### A2 (Single-Valued, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 10 000    | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 856 808 | 2 683 034 | 2 415 884 | 2 385 776 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 1000 runs

| Metric   | Min       | Max       | Median   | Mean   |
| --------- | --------- | --------- | --------- | --------- |
| Impressions    | 10 000    | 10 000    | 10 000    | 10 000    |
| Fill rate | 100.0%    | 100.0%    | 100.0%    | 100.0%    |
| Revenue   | 1 733 559 | 2 683 073 | 2 403 541 | 2 380 161 |

> Distribution of impressions: 0 (0.0% from average)


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -11.6%
- **A3 vs best_price**: impressions +0.0%, revenue -11.8%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
## 22 Scenario: Company 100, 100K query, balanced

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 100 |
| Requests | 100 000 |
| Type of traffic | Balanced |
| Total volume (A2) | 1 058 076 impressions |
| Total budget (A3) | 161 882 690 units. |
| Mean CPM | 149.8 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 42 028      | 11 767 840  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 60 514      | 9 682 240   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 48 545      | 6 796 300   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 17 419      | 1 567 710   |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 25 536      | 6 384 000   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 47 005      | 9 401 000   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 28 728      | 9 192 960   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 26 572      | 3 454 360   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 38 500      | 5 775 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 10 556      | 2 111 200   |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 13 789      | 2 757 800   |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 10 219      | 1 635 040   |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 9 197       | 1 011 670   |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 26 460      | 2 116 800   |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 7 559       | 755 900     |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 20 173      | 2 420 760   |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 21 112      | 2 111 200   |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 32 074      | 5 452 580   |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 19 684      | 4 724 160   |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 31 499      | 3 464 890   |
| Bank_5604b370baee11e8 | 19.0%      | 300 | 4.5       | 13 300      | 3 990 000   |
| Retail_4765ba374f6aecc1 | 27.0%      | 130 | 3.5       | 18 907      | 2 457 910   |
| Telecom_ed706ab0d06977cd | 14.0%      | 140 | 3.5       | 9 800       | 1 372 000   |
| Retail_c08a2c8e2aaba579 | 23.0%      | 100 | 3.0       | 16 099      | 1 609 900   |
| Campaign_7dc611819a260eaf | 15.0%      | 110 | 3.0       | 10 500      | 1 155 000   |
| Campaign_0ec7f92f18e461bb | 10.5%      | 80  | 2.5       | 7 349       | 587 920     |
| Campaign_9d1008b88789df38 | 11.9%      | 280 | 4.0       | 8 346       | 2 336 880   |
| Campaign_0cc18fd853a12790 | 11.2%      | 400 | 5.0       | 7 811       | 3 124 400   |
| Health_6443f22d5852d528 | 43.5%      | 160 | 3.5       | 30 415      | 4 866 400   |
| Campaign_9b4d1a7d25db93e0 | 45.8%      | 90  | 3.0       | 32 074      | 2 886 660   |
| Bank_412b1a6e792a6b27 | 19.0%      | 150 | 4.0       | 13 300      | 1 995 000   |
| Retail_8a95d706a952fc0a | 11.4%      | 92  | 3.1       | 7 979       | 731 674     |
| Campaign_25d7a2ecf9a34029 | 21.5%      | 127 | 3.7       | 15 021      | 1 903 161   |
| Campaign_320311c675dff6d8 | 2.6%       | 100 | 2.8       | 1 847       | 184 700     |
| Retail_1f18939ad657c07d | 3.3%       | 137 | 3.4       | 2 293       | 313 453     |
| Automotive_0386a6443f12a5ec | 1.1%       | 263 | 4.0       | 756         | 199 055     |
| Campaign_d4727b5c19a92dfe | 10.5%      | 120 | 3.1       | 7 349       | 881 880     |
| Bank_c99262d85fa8290e | 6.1%       | 150 | 4.2       | 4 256       | 638 400     |
| Retail_fd2940988420c92e | 5.7%       | 92  | 3.3       | 3 989       | 365 791     |
| Campaign_6f7317281c63b409 | 2.9%       | 127 | 3.9       | 2 030       | 257 201     |
| Campaign_93291ba17bc56b3d | 6.0%       | 100 | 2.5       | 4 200       | 420 000     |
| Retail_c62ca80310d8e264 | 2.8%       | 137 | 3.1       | 1 965       | 268 616     |
| Automotive_e8c4f8cb60890542 | 2.7%       | 263 | 4.2       | 1 864       | 490 791     |
| Campaign_3995407d5cd6a644 | 7.7%       | 120 | 3.3       | 5 390       | 646 800     |
| Bank_b9c2207a5f26e683 | 10.6%      | 150 | 4.4       | 7 447       | 1 117 050   |
| Retail_8ce549b38a2441de | 14.3%      | 92  | 3.0       | 9 975       | 914 708     |
| Campaign_f5af87d0012d3fe4 | 8.7%       | 127 | 3.6       | 6 090       | 771 603     |
| Campaign_ac250cdeb965d918 | 1.9%       | 100 | 2.7       | 1 343       | 134 300     |
| Retail_2c64438c3bb04f75 | 1.4%       | 137 | 3.3       | 982         | 134 239     |
| Automotive_878a8e7c40af35fd | 0.4%       | 263 | 4.4       | 252         | 66 352      |
| Campaign_96b37a70e8bdba6c | 17.5%      | 120 | 3.0       | 12 250      | 1 470 000   |
| Bank_d4ac740fdbbfe6b0 | 9.1%       | 150 | 4.1       | 6 384       | 957 600     |
| Retail_d5a9402ae3c29c35 | 35.1%      | 92  | 3.2       | 24 605      | 2 256 278   |
| Campaign_1745b225a2e0be46 | 6.4%       | 127 | 3.8       | 4 466       | 565 842     |
| Campaign_c36fd267e3128ae2 | 3.4%       | 100 | 2.9       | 2 352       | 235 200     |
| Retail_5be29648bbf06d3f | 3.5%       | 137 | 3.0       | 2 457       | 335 872     |
| Automotive_6ac00073f2474735 | 1.1%       | 263 | 4.1       | 756         | 199 055     |
| Campaign_c4fe2cd3875e7055 | 5.6%       | 120 | 3.2       | 3 919       | 470 280     |
| Bank_d4d4acde026fc4a8 | 4.6%       | 150 | 4.3       | 3 192       | 478 800     |
| Retail_0390e1bd6c0c7aa8 | 4.8%       | 92  | 3.4       | 3 325       | 304 902     |
| Campaign_c74dce135eae7c52 | 14.5%      | 127 | 3.5       | 10 150      | 1 286 005   |
| Campaign_59fdd82d61a7f646 | 2.9%       | 100 | 2.6       | 2 015       | 201 500     |
| Retail_694c6720f451703a | 8.7%       | 137 | 3.2       | 6 060       | 828 402     |
| Automotive_a299e1a2466e6aeb | 0.8%       | 263 | 4.3       | 554         | 145 868     |
| Campaign_4706c393b25fb3f0 | 9.8%       | 120 | 3.4       | 6 860       | 823 200     |
| Bank_435aedebb1bf7a2d | 11.4%      | 150 | 4.0       | 7 980       | 1 197 000   |
| Retail_53e8d88f3a226e00 | 14.2%      | 92  | 3.1       | 9 974       | 914 616     |
| Campaign_f9273b882fb2cc0c | 4.6%       | 127 | 3.7       | 3 248       | 411 522     |
| Campaign_ae23878b7e8a0ec1 | 1.4%       | 100 | 2.8       | 1 007       | 100 700     |
| Retail_06f2cf00d35adbca | 1.2%       | 137 | 3.4       | 819         | 111 957     |
| Automotive_f4f5b93b3116fba3 | 1.8%       | 263 | 4.0       | 1 260       | 331 758     |
| Campaign_089e705cd41af878 | 8.4%       | 120 | 3.1       | 5 880       | 705 600     |
| Bank_31ea3c607fa2ed52 | 28.1%      | 150 | 4.2       | 19 684      | 2 952 600   |
| Retail_cbef4c4fbb517dd1 | 10.4%      | 92  | 3.3       | 7 314       | 670 694     |
| Campaign_4c3aa0fbe837f21f | 8.1%       | 127 | 3.9       | 5 684       | 720 163     |
| Campaign_ea02a7e77d42a558 | 3.6%       | 100 | 2.5       | 2 520       | 252 000     |
| Retail_ba29207cfea4b3f6 | 3.5%       | 137 | 3.1       | 2 457       | 335 872     |
| Automotive_cef55d2ad4127179 | 0.6%       | 263 | 4.2       | 403         | 106 110     |
| Campaign_95afde8bce1ca2fd | 4.2%       | 120 | 3.3       | 2 940       | 352 800     |
| Bank_8de7e73806d62f7f | 3.8%       | 150 | 4.4       | 2 660       | 399 000     |
| Retail_9d523ac2afb377fc | 23.8%      | 92  | 3.0       | 16 625      | 1 524 512   |
| Campaign_d8646f2deca6903a | 7.0%       | 127 | 3.6       | 4 872       | 617 282     |
| Campaign_2bd323ca0951e219 | 8.9%       | 100 | 2.7       | 6 215       | 621 500     |
| Retail_3f81958b91b44b57 | 2.6%       | 137 | 3.3       | 1 801       | 246 197     |
| Automotive_6d602705b3344057 | 1.0%       | 263 | 4.4       | 705         | 185 626     |
| Campaign_745dba57acaf7918 | 10.5%      | 120 | 3.0       | 7 350       | 882 000     |
| Bank_0abaaf432ed16231 | 11.4%      | 150 | 4.1       | 7 979       | 1 196 850   |
| Retail_0fde75a9a148a512 | 7.6%       | 92  | 3.2       | 5 320       | 487 844     |
| Campaign_a90aa3ddd1a54bbc | 3.5%       | 127 | 3.8       | 2 436       | 308 641     |
| Campaign_40e1d170d51e276f | 1.2%       | 100 | 2.9       | 840         | 84 000      |
| Retail_ee5b98dcb1e20583 | 5.8%       | 137 | 3.0       | 4 094       | 559 650     |
| Automotive_3f50906f88bf8469 | 0.9%       | 263 | 4.1       | 604         | 159 033     |
| Campaign_b4381361bcb690b9 | 25.9%      | 120 | 3.2       | 18 130      | 2 175 600   |
| Bank_c142b51224633f3a | 8.4%       | 150 | 4.3       | 5 852       | 877 800     |
| Retail_48fb5a3bfa1a566c | 13.3%      | 92  | 3.4       | 9 310       | 853 727     |
| Campaign_ec0134764fd02d46 | 8.7%       | 127 | 3.5       | 6 090       | 771 603     |
| Campaign_3c4832e7fc1e1e90 | 3.6%       | 100 | 2.6       | 2 519       | 251 900     |
| Retail_f01b7bcd1d812f00 | 1.9%       | 137 | 3.2       | 1 310       | 179 077     |
| Automotive_4f12f5c2a0f07630 | 0.4%       | 263 | 4.3       | 302         | 79 517      |
| Campaign_afd3cf7367db1093 | 3.5%       | 120 | 3.4       | 2 449       | 293 880     |

#### Classical Strategies (1 run)

| Strategy         | Impressions  | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------- | --------- | --------- | ---------- | ------------ |
| best_one          | 100 000 | 100.0%    | 0.0%      | 21 356 980 | 213.6        |
| random_one        | 100 000 | 100.0%    | 0.0%      | 14 808 791 | 148.1        |
| best_price        | 100 000 | 100.0%    | 0.0%      | 26 504 875 | 265.0        |
| random_price      | 100 000 | 100.0%    | 0.0%      | 16 695 232 | 167.0        |
| best_velocity     | 100 000 | 100.0%    | 0.0%      | 15 299 834 | 153.0        |
| random_velocity   | 100 000 | 100.0%    | 0.0%      | 14 824 875 | 148.2        |
| best_heuristics   | 100 000 | 100.0%    | 0.0%      | 25 231 778 | 252.3        |
| random_heuristics | 100 000 | 100.0%    | 0.0%      | 17 336 023 | 173.4        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 100 000    | 100 000    | 100 000    | 100 000    |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 18 830 063 | 26 111 254 | 23 575 049 | 23 322 142 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 100 000    | 100 000    | 100 000    | 100 000    |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 18 612 809 | 26 252 722 | 23 708 282 | 23 349 433 |

> Distribution of impressions: 0 (0.0% from average)


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -12.0%
- **A3 vs best_price**: impressions +0.0%, revenue -11.9%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)

---
## 23 Scenario: Company 100, 100K queries, shortage

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 100 |
| Requests | 100 000 |
| Type of traffic | Lack of traffic |
| Total volume (A2) | 332 514 impressions |
| Total budget (A3) | 50 873 628 units. |
| Mean CPM | 149.8 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 13 208      | 3 698 240   |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 19 019      | 3 043 040   |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 15 257      | 2 135 980   |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 5 474       | 492 660     |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 8 025       | 2 006 250   |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 14 773      | 2 954 600   |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 9 028       | 2 888 960   |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 8 351       | 1 085 630   |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 12 100      | 1 815 000   |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 3 317       | 663 400     |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 4 333       | 866 600     |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 3 211       | 513 760     |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 2 890       | 317 900     |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 8 316       | 665 280     |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 2 375       | 237 500     |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 6 340       | 760 800     |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 6 635       | 663 500     |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 10 080      | 1 713 600   |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 6 186       | 1 484 640   |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 9 899       | 1 088 890   |
| Bank_5604b370baee11e8 | 19.0%      | 300 | 4.5       | 4 180       | 1 254 000   |
| Retail_4765ba374f6aecc1 | 27.0%      | 130 | 3.5       | 5 942       | 772 460     |
| Telecom_ed706ab0d06977cd | 14.0%      | 140 | 3.5       | 3 080       | 431 200     |
| Retail_c08a2c8e2aaba579 | 23.0%      | 100 | 3.0       | 5 060       | 506 000     |
| Campaign_7dc611819a260eaf | 15.0%      | 110 | 3.0       | 3 300       | 363 000     |
| Campaign_0ec7f92f18e461bb | 10.5%      | 80  | 2.5       | 2 310       | 184 800     |
| Campaign_9d1008b88789df38 | 11.9%      | 280 | 4.0       | 2 623       | 734 440     |
| Campaign_0cc18fd853a12790 | 11.2%      | 400 | 5.0       | 2 455       | 982 000     |
| Health_6443f22d5852d528 | 43.5%      | 160 | 3.5       | 9 559       | 1 529 440   |
| Campaign_9b4d1a7d25db93e0 | 45.8%      | 90  | 3.0       | 10 080      | 907 200     |
| Bank_412b1a6e792a6b27 | 19.0%      | 150 | 4.0       | 4 180       | 627 000     |
| Retail_8a95d706a952fc0a | 11.4%      | 92  | 3.1       | 2 507       | 229 892     |
| Campaign_25d7a2ecf9a34029 | 21.5%      | 127 | 3.7       | 4 721       | 598 151     |
| Campaign_320311c675dff6d8 | 2.6%       | 100 | 2.8       | 580         | 58 000      |
| Retail_1f18939ad657c07d | 3.3%       | 137 | 3.4       | 720         | 98 424      |
| Automotive_0386a6443f12a5ec | 1.1%       | 263 | 4.0       | 237         | 62 402      |
| Campaign_d4727b5c19a92dfe | 10.5%      | 120 | 3.1       | 2 310       | 277 200     |
| Bank_c99262d85fa8290e | 6.1%       | 150 | 4.2       | 1 337       | 200 550     |
| Retail_fd2940988420c92e | 5.7%       | 92  | 3.3       | 1 253       | 114 900     |
| Campaign_6f7317281c63b409 | 2.9%       | 127 | 3.9       | 638         | 80 835      |
| Campaign_93291ba17bc56b3d | 6.0%       | 100 | 2.5       | 1 320       | 132 000     |
| Retail_c62ca80310d8e264 | 2.8%       | 137 | 3.1       | 617         | 84 344      |
| Automotive_e8c4f8cb60890542 | 2.7%       | 263 | 4.2       | 586         | 154 294     |
| Campaign_3995407d5cd6a644 | 7.7%       | 120 | 3.3       | 1 694       | 203 280     |
| Bank_b9c2207a5f26e683 | 10.6%      | 150 | 4.4       | 2 340       | 351 000     |
| Retail_8ce549b38a2441de | 14.3%      | 92  | 3.0       | 3 135       | 287 480     |
| Campaign_f5af87d0012d3fe4 | 8.7%       | 127 | 3.6       | 1 914       | 242 504     |
| Campaign_ac250cdeb965d918 | 1.9%       | 100 | 2.7       | 422         | 42 200      |
| Retail_2c64438c3bb04f75 | 1.4%       | 137 | 3.3       | 308         | 42 104      |
| Automotive_878a8e7c40af35fd | 0.4%       | 263 | 4.4       | 79          | 20 801      |
| Campaign_96b37a70e8bdba6c | 17.5%      | 120 | 3.0       | 3 850       | 462 000     |
| Bank_d4ac740fdbbfe6b0 | 9.1%       | 150 | 4.1       | 2 006       | 300 900     |
| Retail_d5a9402ae3c29c35 | 35.1%      | 92  | 3.2       | 7 733       | 709 116     |
| Campaign_1745b225a2e0be46 | 6.4%       | 127 | 3.8       | 1 403       | 177 760     |
| Campaign_c36fd267e3128ae2 | 3.4%       | 100 | 2.9       | 739         | 73 900      |
| Retail_5be29648bbf06d3f | 3.5%       | 137 | 3.0       | 772         | 105 532     |
| Automotive_6ac00073f2474735 | 1.1%       | 263 | 4.1       | 237         | 62 402      |
| Campaign_c4fe2cd3875e7055 | 5.6%       | 120 | 3.2       | 1 231       | 147 720     |
| Bank_d4d4acde026fc4a8 | 4.6%       | 150 | 4.3       | 1 003       | 150 450     |
| Retail_0390e1bd6c0c7aa8 | 4.8%       | 92  | 3.4       | 1 045       | 95 826      |
| Campaign_c74dce135eae7c52 | 14.5%      | 127 | 3.5       | 3 190       | 404 173     |
| Campaign_59fdd82d61a7f646 | 2.9%       | 100 | 2.6       | 633         | 63 300      |
| Retail_694c6720f451703a | 8.7%       | 137 | 3.2       | 1 904       | 260 277     |
| Automotive_a299e1a2466e6aeb | 0.8%       | 263 | 4.3       | 174         | 45 814      |
| Campaign_4706c393b25fb3f0 | 9.8%       | 120 | 3.4       | 2 156       | 258 720     |
| Bank_435aedebb1bf7a2d | 11.4%      | 150 | 4.0       | 2 508       | 376 200     |
| Retail_53e8d88f3a226e00 | 14.2%      | 92  | 3.1       | 3 134       | 287 388     |
| Campaign_f9273b882fb2cc0c | 4.6%       | 127 | 3.7       | 1 020       | 129 234     |
| Campaign_ae23878b7e8a0ec1 | 1.4%       | 100 | 2.8       | 316         | 31 600      |
| Retail_06f2cf00d35adbca | 1.2%       | 137 | 3.4       | 257         | 35 132      |
| Automotive_f4f5b93b3116fba3 | 1.8%       | 263 | 4.0       | 396         | 104 267     |
| Campaign_089e705cd41af878 | 8.4%       | 120 | 3.1       | 1 848       | 221 760     |
| Bank_31ea3c607fa2ed52 | 28.1%      | 150 | 4.2       | 6 186       | 927 900     |
| Retail_cbef4c4fbb517dd1 | 10.4%      | 92  | 3.3       | 2 299       | 210 818     |
| Campaign_4c3aa0fbe837f21f | 8.1%       | 127 | 3.9       | 1 786       | 226 286     |
| Campaign_ea02a7e77d42a558 | 3.6%       | 100 | 2.5       | 792         | 79 200      |
| Retail_ba29207cfea4b3f6 | 3.5%       | 137 | 3.1       | 772         | 105 532     |
| Automotive_cef55d2ad4127179 | 0.6%       | 263 | 4.2       | 126         | 33 176      |
| Campaign_95afde8bce1ca2fd | 4.2%       | 120 | 3.3       | 924         | 110 880     |
| Bank_8de7e73806d62f7f | 3.8%       | 150 | 4.4       | 836         | 125 400     |
| Retail_9d523ac2afb377fc | 23.8%      | 92  | 3.0       | 5 225       | 479 132     |
| Campaign_d8646f2deca6903a | 7.0%       | 127 | 3.6       | 1 531       | 193 978     |
| Campaign_2bd323ca0951e219 | 8.9%       | 100 | 2.7       | 1 953       | 195 300     |
| Retail_3f81958b91b44b57 | 2.6%       | 137 | 3.3       | 566         | 77 372      |
| Automotive_6d602705b3344057 | 1.0%       | 263 | 4.4       | 221         | 58 189      |
| Campaign_745dba57acaf7918 | 10.5%      | 120 | 3.0       | 2 310       | 277 200     |
| Bank_0abaaf432ed16231 | 11.4%      | 150 | 4.1       | 2 507       | 376 050     |
| Retail_0fde75a9a148a512 | 7.6%       | 92  | 3.2       | 1 672       | 153 322     |
| Campaign_a90aa3ddd1a54bbc | 3.5%       | 127 | 3.8       | 765         | 96 926      |
| Campaign_40e1d170d51e276f | 1.2%       | 100 | 2.9       | 264         | 26 400      |
| Retail_ee5b98dcb1e20583 | 5.8%       | 137 | 3.0       | 1 287       | 175 933     |
| Automotive_3f50906f88bf8469 | 0.9%       | 263 | 4.1       | 190         | 50 027      |
| Campaign_b4381361bcb690b9 | 25.9%      | 120 | 3.2       | 5 698       | 683 760     |
| Bank_c142b51224633f3a | 8.4%       | 150 | 4.3       | 1 839       | 275 850     |
| Retail_48fb5a3bfa1a566c | 13.3%      | 92  | 3.4       | 2 926       | 268 314     |
| Campaign_ec0134764fd02d46 | 8.7%       | 127 | 3.5       | 1 914       | 242 504     |
| Campaign_3c4832e7fc1e1e90 | 3.6%       | 100 | 2.6       | 791         | 79 100      |
| Retail_f01b7bcd1d812f00 | 1.9%       | 137 | 3.2       | 411         | 56 184      |
| Automotive_4f12f5c2a0f07630 | 0.4%       | 263 | 4.3       | 95          | 25 014      |
| Campaign_afd3cf7367db1093 | 3.5%       | 120 | 3.4       | 769         | 92 280      |

#### Classical Strategies (1 run)

| Strategy         | Impressions  | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------- | --------- | --------- | ---------- | ------------ |
| best_one          | 100 000 | 100.0%    | 0.0%      | 18 964 640 | 189.6        |
| random_one        | 100 000 | 100.0%    | 0.0%      | 14 808 791 | 148.1        |
| best_price        | 100 000 | 100.0%    | 0.0%      | 22 763 618 | 227.6        |
| random_price      | 100 000 | 100.0%    | 0.0%      | 16 694 828 | 166.9        |
| best_velocity     | 100 000 | 100.0%    | 0.0%      | 15 299 599 | 153.0        |
| random_velocity   | 100 000 | 100.0%    | 0.0%      | 14 858 489 | 148.6        |
| best_heuristics   | 100 000 | 100.0%    | 0.0%      | 20 293 504 | 202.9        |
| random_heuristics | 100 000 | 100.0%    | 0.0%      | 17 066 002 | 170.7        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 984     | 100 000    | 100 000    | 99 999     |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 15 856 015 | 22 488 235 | 20 017 546 | 19 923 669 |

> Distribution of impressions: 16 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 99 975     | 100 000    | 100 000    | 99 999     |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 16 481 157 | 22 278 114 | 20 116 518 | 19 922 550 |

> Distribution of impressions: 25 (0.0% from average)


#### Conclusion on applicability

- **A2 vs best_price**: impressions -0.0%, revenue -12.5%
- **A3 vs best_price**: impressions -0.0%, revenue -12.5%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Lack of traffic**: All algorithms are limited by the number of ads available; adwords may show slightly less due to random prices.

---
## 24 Scenario : Company 100, 100K queries, excess

### Scenario conditions

| Parameter | Value |
|----------|----------|
| Campaigns | 100 |
| Requests | 100 000 |
| Type of traffic | Excess traffic |
| Total volume (A2) | 4 534 732 impressions |
| Total budget (A3) | 693 799 466 units. |
| Mean CPM | 149.8 |

#### Participating companies

| Campaign         | Match rate | CPM | Priority | Volume (A2) | Budget (A3) |
| ---------------- | ---------- | --- | --------- | ----------- | ----------- |
| Bank_24d40196bd94b649 | 60.0%      | 280 | 5.0       | 180 120     | 50 433 600  |
| Telecom_d46ed517452394a2 | 86.4%      | 160 | 4.0       | 259 350     | 41 496 000  |
| Retail_59c52779836b2bae | 69.3%      | 140 | 3.5       | 208 050     | 29 127 000  |
| Campaign_51288482374d537c | 24.9%      | 90  | 3.0       | 74 654      | 6 718 860   |
| Automotive_9e1edff89ac9a790 | 36.5%      | 250 | 4.5       | 109 440     | 27 360 000  |
| Campaign_4d4dc901c2e49788 | 67.2%      | 200 | 4.0       | 201 450     | 40 290 000  |
| Property_5a34d256a53751c3 | 41.0%      | 320 | 4.5       | 123 120     | 39 398 400  |
| Retail_5d131e8ff2fd6390 | 38.0%      | 130 | 3.0       | 113 880     | 14 804 400  |
| Health_0676356d6ba137b6 | 55.0%      | 150 | 3.5       | 165 000     | 24 750 000  |
| Travel_3724963d1920e16a | 15.1%      | 200 | 3.5       | 45 240      | 9 048 000   |
| Bank_93461467de106ae8 | 19.7%      | 200 | 4.0       | 59 097      | 11 819 400  |
| Retail_6162b5875d2e4e9b | 14.6%      | 160 | 3.5       | 43 799      | 7 007 840   |
| Retail_8846b13f4335d7b7 | 13.1%      | 110 | 3.0       | 39 419      | 4 336 090   |
| Campaign_a54822eb2c43abe7 | 37.8%      | 80  | 3.0       | 113 400     | 9 072 000   |
| Campaign_04055ec242bc0613 | 10.8%      | 100 | 3.0       | 32 399      | 3 239 900   |
| Property_db25972d5f786d2e | 28.8%      | 120 | 3.5       | 86 457      | 10 374 840  |
| Children_90daa9b022baf620 | 30.2%      | 100 | 3.0       | 90 480      | 9 048 000   |
| Travel_a0a6420a0d37809f | 45.8%      | 170 | 3.5       | 137 460     | 23 368 200  |
| Bank_fbe065970201fb55 | 28.1%      | 240 | 4.0       | 84 360      | 20 246 400  |
| Campaign_d5e7563f29a5b384 | 45.0%      | 110 | 3.0       | 134 999     | 14 849 890  |
| Bank_5604b370baee11e8 | 19.0%      | 300 | 4.5       | 57 000      | 17 100 000  |
| Retail_4765ba374f6aecc1 | 27.0%      | 130 | 3.5       | 81 030      | 10 533 900  |
| Telecom_ed706ab0d06977cd | 14.0%      | 140 | 3.5       | 42 000      | 5 880 000   |
| Retail_c08a2c8e2aaba579 | 23.0%      | 100 | 3.0       | 69 000      | 6 900 000   |
| Campaign_7dc611819a260eaf | 15.0%      | 110 | 3.0       | 45 000      | 4 950 000   |
| Campaign_0ec7f92f18e461bb | 10.5%      | 80  | 2.5       | 31 500      | 2 520 000   |
| Campaign_9d1008b88789df38 | 11.9%      | 280 | 4.0       | 35 769      | 10 015 320  |
| Campaign_0cc18fd853a12790 | 11.2%      | 400 | 5.0       | 33 477      | 13 390 800  |
| Health_6443f22d5852d528 | 43.5%      | 160 | 3.5       | 130 350     | 20 856 000  |
| Campaign_9b4d1a7d25db93e0 | 45.8%      | 90  | 3.0       | 137 460     | 12 371 400  |
| Bank_412b1a6e792a6b27 | 19.0%      | 150 | 4.0       | 57 000      | 8 550 000   |
| Retail_8a95d706a952fc0a | 11.4%      | 92  | 3.1       | 34 199      | 3 136 048   |
| Campaign_25d7a2ecf9a34029 | 21.5%      | 127 | 3.7       | 64 380      | 8 156 946   |
| Campaign_320311c675dff6d8 | 2.6%       | 100 | 2.8       | 7 920       | 792 000     |
| Retail_1f18939ad657c07d | 3.3%       | 137 | 3.4       | 9 827       | 1 343 351   |
| Automotive_0386a6443f12a5ec | 1.1%       | 263 | 4.0       | 3 240       | 853 092     |
| Campaign_d4727b5c19a92dfe | 10.5%      | 120 | 3.1       | 31 500      | 3 780 000   |
| Bank_c99262d85fa8290e | 6.1%       | 150 | 4.2       | 18 240      | 2 736 000   |
| Retail_fd2940988420c92e | 5.7%       | 92  | 3.3       | 17 099      | 1 567 978   |
| Campaign_6f7317281c63b409 | 2.9%       | 127 | 3.9       | 8 700       | 1 102 290   |
| Campaign_93291ba17bc56b3d | 6.0%       | 100 | 2.5       | 18 000      | 1 800 000   |
| Retail_c62ca80310d8e264 | 2.8%       | 137 | 3.1       | 8 423       | 1 151 424   |
| Automotive_e8c4f8cb60890542 | 2.7%       | 263 | 4.2       | 7 992       | 2 104 294   |
| Campaign_3995407d5cd6a644 | 7.7%       | 120 | 3.3       | 23 100      | 2 772 000   |
| Bank_b9c2207a5f26e683 | 10.6%      | 150 | 4.4       | 31 920      | 4 788 000   |
| Retail_8ce549b38a2441de | 14.3%      | 92  | 3.0       | 42 750      | 3 920 175   |
| Campaign_f5af87d0012d3fe4 | 8.7%       | 127 | 3.6       | 26 100      | 3 306 870   |
| Campaign_ac250cdeb965d918 | 1.9%       | 100 | 2.7       | 5 759       | 575 900     |
| Retail_2c64438c3bb04f75 | 1.4%       | 137 | 3.3       | 4 211       | 575 644     |
| Automotive_878a8e7c40af35fd | 0.4%       | 263 | 4.4       | 1 080       | 284 364     |
| Campaign_96b37a70e8bdba6c | 17.5%      | 120 | 3.0       | 52 500      | 6 300 000   |
| Bank_d4ac740fdbbfe6b0 | 9.1%       | 150 | 4.1       | 27 360      | 4 104 000   |
| Retail_d5a9402ae3c29c35 | 35.1%      | 92  | 3.2       | 105 450     | 9 669 765   |
| Campaign_1745b225a2e0be46 | 6.4%       | 127 | 3.8       | 19 140      | 2 425 038   |
| Campaign_c36fd267e3128ae2 | 3.4%       | 100 | 2.9       | 10 080      | 1 008 000   |
| Retail_5be29648bbf06d3f | 3.5%       | 137 | 3.0       | 10 530      | 1 439 451   |
| Automotive_6ac00073f2474735 | 1.1%       | 263 | 4.1       | 3 240       | 853 092     |
| Campaign_c4fe2cd3875e7055 | 5.6%       | 120 | 3.2       | 16 799      | 2 015 880   |
| Bank_d4d4acde026fc4a8 | 4.6%       | 150 | 4.3       | 13 680      | 2 052 000   |
| Retail_0390e1bd6c0c7aa8 | 4.8%       | 92  | 3.4       | 14 250      | 1 306 725   |
| Campaign_c74dce135eae7c52 | 14.5%      | 127 | 3.5       | 43 500      | 5 511 450   |
| Campaign_59fdd82d61a7f646 | 2.9%       | 100 | 2.6       | 8 640       | 864 000     |
| Retail_694c6720f451703a | 8.7%       | 137 | 3.2       | 25 974      | 3 550 646   |
| Automotive_a299e1a2466e6aeb | 0.8%       | 263 | 4.3       | 2 376       | 625 601     |
| Campaign_4706c393b25fb3f0 | 9.8%       | 120 | 3.4       | 29 400      | 3 528 000   |
| Bank_435aedebb1bf7a2d | 11.4%      | 150 | 4.0       | 34 200      | 5 130 000   |
| Retail_53e8d88f3a226e00 | 14.2%      | 92  | 3.1       | 42 749      | 3 920 083   |
| Campaign_f9273b882fb2cc0c | 4.6%       | 127 | 3.7       | 13 920      | 1 763 664   |
| Campaign_ae23878b7e8a0ec1 | 1.4%       | 100 | 2.8       | 4 320       | 432 000     |
| Retail_06f2cf00d35adbca | 1.2%       | 137 | 3.4       | 3 510       | 479 817     |
| Automotive_f4f5b93b3116fba3 | 1.8%       | 263 | 4.0       | 5 400       | 1 421 820   |
| Campaign_089e705cd41af878 | 8.4%       | 120 | 3.1       | 25 200      | 3 024 000   |
| Bank_31ea3c607fa2ed52 | 28.1%      | 150 | 4.2       | 84 360      | 12 654 000  |
| Retail_cbef4c4fbb517dd1 | 10.4%      | 92  | 3.3       | 31 350      | 2 874 795   |
| Campaign_4c3aa0fbe837f21f | 8.1%       | 127 | 3.9       | 24 360      | 3 086 412   |
| Campaign_ea02a7e77d42a558 | 3.6%       | 100 | 2.5       | 10 800      | 1 080 000   |
| Retail_ba29207cfea4b3f6 | 3.5%       | 137 | 3.1       | 10 530      | 1 439 451   |
| Automotive_cef55d2ad4127179 | 0.6%       | 263 | 4.2       | 1 728       | 454 982     |
| Campaign_95afde8bce1ca2fd | 4.2%       | 120 | 3.3       | 12 600      | 1 512 000   |
| Bank_8de7e73806d62f7f | 3.8%       | 150 | 4.4       | 11 400      | 1 710 000   |
| Retail_9d523ac2afb377fc | 23.8%      | 92  | 3.0       | 71 250      | 6 533 625   |
| Campaign_d8646f2deca6903a | 7.0%       | 127 | 3.6       | 20 880      | 2 645 496   |
| Campaign_2bd323ca0951e219 | 8.9%       | 100 | 2.7       | 26 639      | 2 663 900   |
| Retail_3f81958b91b44b57 | 2.6%       | 137 | 3.3       | 7 722       | 1 055 597   |
| Automotive_6d602705b3344057 | 1.0%       | 263 | 4.4       | 3 024       | 796 219     |
| Campaign_745dba57acaf7918 | 10.5%      | 120 | 3.0       | 31 500      | 3 780 000   |
| Bank_0abaaf432ed16231 | 11.4%      | 150 | 4.1       | 34 199      | 5 129 850   |
| Retail_0fde75a9a148a512 | 7.6%       | 92  | 3.2       | 22 800      | 2 090 760   |
| Campaign_a90aa3ddd1a54bbc | 3.5%       | 127 | 3.8       | 10 440      | 1 322 748   |
| Campaign_40e1d170d51e276f | 1.2%       | 100 | 2.9       | 3 600       | 360 000     |
| Retail_ee5b98dcb1e20583 | 5.8%       | 137 | 3.0       | 17 550      | 2 399 085   |
| Automotive_3f50906f88bf8469 | 0.9%       | 263 | 4.1       | 2 592       | 682 474     |
| Campaign_b4381361bcb690b9 | 25.9%      | 120 | 3.2       | 77 700      | 9 324 000   |
| Bank_c142b51224633f3a | 8.4%       | 150 | 4.3       | 25 080      | 3 762 000   |
| Retail_48fb5a3bfa1a566c | 13.3%      | 92  | 3.4       | 39 900      | 3 658 830   |
| Campaign_ec0134764fd02d46 | 8.7%       | 127 | 3.5       | 26 100      | 3 306 870   |
| Campaign_3c4832e7fc1e1e90 | 3.6%       | 100 | 2.6       | 10 799      | 1 079 900   |
| Retail_f01b7bcd1d812f00 | 1.9%       | 137 | 3.2       | 5 616       | 767 707     |
| Automotive_4f12f5c2a0f07630 | 0.4%       | 263 | 4.3       | 1 296       | 341 237     |
| Campaign_afd3cf7367db1093 | 3.5%       | 120 | 3.4       | 10 499      | 1 259 880   |

#### Classical Strategies (1 run)

| Strategy         | Impressions  | Fill rate | Miss rate | Revenue    | Avg.CPM/display |
| ----------------- | ------- | --------- | --------- | ---------- | ------------ |
| best_one          | 100 000 | 100.0%    | 0.0%      | 23 460 470 | 234.6        |
| random_one        | 100 000 | 100.0%    | 0.0%      | 14 808 791 | 148.1        |
| best_price        | 100 000 | 100.0%    | 0.0%      | 26 910 809 | 269.1        |
| random_price      | 100 000 | 100.0%    | 0.0%      | 16 695 232 | 167.0        |
| best_velocity     | 100 000 | 100.0%    | 0.0%      | 15 299 735 | 153.0        |
| random_velocity   | 100 000 | 100.0%    | 0.0%      | 14 819 205 | 148.2        |
| best_heuristics   | 100 000 | 100.0%    | 0.0%      | 26 559 956 | 265.6        |
| random_heuristics | 100 000 | 100.0%    | 0.0%      | 17 424 003 | 174.2        |

#### A2 (Single-Valued, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 100 000    | 100 000    | 100 000    | 100 000    |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 19 032 557 | 26 545 969 | 24 037 035 | 23 794 482 |

> Distribution of impressions: 0 (0.0% from average)

#### A3 (Small Budget, Vazirani) - 300 runs

| Metric   | Min        | Max        | Median    | Mean    |
| --------- | ---------- | ---------- | ---------- | ---------- |
| Impressions    | 100 000    | 100 000    | 100 000    | 100 000    |
| Fill rate | 100.0%     | 100.0%     | 100.0%     | 100.0%     |
| Revenue   | 18 856 176 | 26 678 974 | 24 121 188 | 23 790 890 |

> Distribution of impressions: 0 (0.0% from average)


#### Conclusion on applicability

- **A2 vs best_price**: impressions +0.0%, revenue -11.6%
- **A3 vs best_price**: impressions +0.0%, revenue -11.6%
- **A2 stability**: high (0.0% scatter)
- **A3 stability**: high (0.0% scatter)
- **Excess traffic**: Volume is not a limitation; the difference in algorithms is only in the distribution of revenue across companies.

---
