# Open run of `baseline50_check`

Parameters: {"sample": 0.007618114755502092, "q": 0.8, "policy": "random", "pool_devices": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "days": [0, 4], "seed": 42, "prepared_signature": "8d878284379be2535b0445785f09ebecfda7c718308eb51ed2df9c4ec8ee5a81", "prepared_source": "/home/gnevich/auction_platform/benchmarks/log_benchmark/../logs/janus_20261012_20261019.parquet", "manager_ads": "benchmarks/closed_stand/manager_baseline50_20261012.json", "our_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/../log_benchmark/ads_manual.json", "manager_price": 150.0, "fallback_204": false}

### Open run (learning log)

| Politics | Days | Sent / pool | Sent / traffic | Sell-through (200/gone) | 200 / pool | 200 piece | Manager’s revenue | Revenue from ours | Total |
|---|---|---|---|---|---|---|---|---|---|
| random | 0:4 | 80.02% | 46.63% | 47.39% | 37.92% | 223 574 | 33 536 100 | 116 734 905 | 150 271 005 |

Relative to `random` (same volume):

#### `random` - by day

| Day | Requests | Pool | Sent | Sent/pool | 200 | Sell-through |
|---|---|---|---|---|---|---|
| 0 | 248 142 | 145 335 | 116 430 | 80.11% | 55 689 | 47.83% |
| 1 | 271 876 | 147 607 | 118 194 | 80.07% | 55 940 | 47.33% |
| 2 | 260 657 | 149 502 | 119 578 | 79.98% | 55 730 | 46.61% |
| 3 | 231 066 | 147 094 | 117 537 | 79.91% | 56 215 | 47.83% |

Our companies (`random`): sold 530 298 impressions, without targeting 0.00%, cut off by 1.80% filters from queries that have reached ours.

| Campaign | cpm | volume | impressions | sell-out | revenue |
|---|---|---|---|---|---|
| Bank_24d40196bd94b649 | 280.0 | 78 370 | 78 370 | 100.00% | 21 943 600 |
| Telecom_d46ed517452394a2 | 160.0 | 114 447 | 37 666 | 32.91% | 6 026 560 |
| Retail_59c52779836b2bae | 140.0 | 93 223 | 15 197 | 16.30% | 2 127 580 |
| Campaign_51288482374d537c | 90.0 | 68 913 | 501 | 0.73% | 45 090 |
| Automotive_9e1edff89ac9a790 | 250.0 | 50 536 | 50 536 | 100.00% | 12 634 000 |
| Campaign_4d4dc901c2e49788 | 200.0 | 99 489 | 99 489 | 100.00% | 19 897 800 |
| Property_5a34d256a53751c3 | 320.0 | 67 444 | 67 444 | 100.00% | 21 582 080 |
| Retail_5d131e8ff2fd6390 | 130.0 | 28 877 | 16 515 | 57.19% | 2 146 950 |
| Health_0676356d6ba137b6 | 150.0 | 10 201 | 340 | 3.33% | 51 000 |
| Travel_3724963d1920e16a | 200.0 | 11 259 | 7 306 | 64.89% | 1 461 200 |
| Bank_93461467de106ae8 | 200.0 | 10 044 | 739 | 7.36% | 147 800 |
| Retail_6162b5875d2e4e9b | 130.0 | 20 018 | 5 775 | 28.85% | 750 750 |
| Children_90daa9b022baf620 | 110.0 | 14 665 | 9 867 | 67.28% | 1 085 370 |
| Children_1aa561689b8b57e7 | 150.0 | 2 857 | 191 | 6.69% | 28 650 |
| Retail_8846b13f4335d7b7 | 120.0 | 4 858 | 291 | 5.99% | 34 920 |
| Entertainment_69bc7e453450b097 | 170.0 | 5 914 | 642 | 10.86% | 109 140 |
| Entertainment_a1dfc2a1e842d0a2 | 220.0 | 20 201 | 5 048 | 24.99% | 1 110 560 |
| Entertainment_9237fb2e70bf48fc | 180.0 | 18 291 | 6 627 | 36.23% | 1 192 860 |
| Campaign_4ada123d5805979b | 100.0 | 10 100 | 7 353 | 72.80% | 735 300 |
| Entertainment_6e3c73f12bc64057 | 90.0 | 6 355 | 322 | 5.07% | 28 980 |
| Retail_de2dbf9477c474eb | 140.0 | 8 880 | 2 422 | 27.27% | 339 080 |
| Health_f41f5144a75c3d01 | 160.0 | 8 495 | 3 880 | 45.67% | 620 800 |
| Bank_1da9a798e900c021 | 300.0 | 10 075 | 10 075 | 100.00% | 3 022 500 |
| Automotive_ee52e22a84292a1f | 210.0 | 1 798 | 511 | 28.42% | 107 310 |
| Campaign_5cb77808ad316b86 | 80.0 | 2 508 | 365 | 14.55% | 29 200 |
| Campaign_c49a8ec579219c40 | 85.0 | 259 | 16 | 6.18% | 1 360 |
| Campaign_8bc4330af9c149de | 95.0 | 4 130 | 18 | 0.44% | 1 710 |
| Campaign_e02df8d0c6b01b69 | 60.0 | 200 312 | 6 537 | 3.26% | 392 220 |
| Campaign_2320b836ad0f2d84 | 75.0 | 121 368 | 15 385 | 12.68% | 1 153 875 |
| Campaign_e5908cfe00510515 | 70.0 | 64 635 | 4 209 | 6.51% | 294 630 |
| Campaign_ee21aa935c0ed10e | 230.0 | 78 370 | 34 324 | 43.80% | 7 894 520 |
| Campaign_f3fec2802fa06a3c | 230.0 | 78 370 | 42 337 | 54.02% | 9 737 510 |

Hidden Manager Companies (`random`, Diagnostics – The Algorithm Cannot See):

| Campaign | volume | 200 | sell-out |
|---|---|---|---|
| Campaign_4d61f9faeb01d35c | 56 917 | 27 037 | 47.50% |
| Campaign_78f39f90f4505c10 | 79 641 | 35 081 | 44.05% |
| Campaign_0823aa18c3c2ca3c | 18 279 | 8 809 | 48.19% |
| Campaign_bfbd684ea6d38f9c | 80 622 | 47 217 | 58.57% |
| Campaign_30b60302c20096a3 | 85 448 | 26 372 | 30.86% |
| Campaign_18a033858fcef7cd | 2 075 | 705 | 33.98% |
| Children_b0f1e3ceb0b3da30 | 1 984 | 673 | 33.92% |
| Campaign_15cc393e200b3c64 | 10 955 | 5 788 | 52.83% |
| Campaign_a16460025af591cd | 23 476 | 5 652 | 24.08% |
| Campaign_82eaaf51f6f9f1de | 29 801 | 8 449 | 28.35% |
| Campaign_b3953d44c96cf68e | 223 919 | 57 791 | 25.81% |
