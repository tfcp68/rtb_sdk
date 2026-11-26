# Open run of `frequency_smoke`

Parameters: {"sample": 0.0022854344266506274, "q": 0.8, "policy": "random", "pool_devices": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "days": [0, 4], "seed": 42, "prepared_signature": "8d878284379be2535b0445785f09ebecfda7c718308eb51ed2df9c4ec8ee5a81", "prepared_source": "/home/gnevich/auction_platform/benchmarks/log_benchmark/../logs/janus_20261012_20261019.parquet", "manager_ads": "benchmarks/closed_stand/manager_calibrated_frequency_20261012.json", "our_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/../log_benchmark/ads_manual.json", "manager_price": 150.0, "fallback_204": false}

### Open run (learning log)

| Politics | Days | Sent / pool | Sent / traffic | Sell-through (200/gone) | 200 / pool | 200 piece | Manager’s revenue | Revenue from ours | Total |
|---|---|---|---|---|---|---|---|---|---|
| random | 0:4 | 80.06% | 47.58% | 37.33% | 29.89% | 51 563 | 7 734 450 | 33 273 200 | 41 007 650 |

Relative to `random` (same volume):

#### `random` - by day

| Day | Requests | Pool | Sent | Sent/pool | 200 | Sell-through |
|---|---|---|---|---|---|---|
| 0 | 71 934 | 42 246 | 33 874 | 80.18% | 12 884 | 38.04% |
| 1 | 79 832 | 44 315 | 35 424 | 79.94% | 13 037 | 36.80% |
| 2 | 73 363 | 42 965 | 34 423 | 80.12% | 12 859 | 37.36% |
| 3 | 65 171 | 43 004 | 34 404 | 80.00% | 12 783 | 37.16% |

Our companies (`random`): sold 150 233 impressions, without targeting 0.00%, cut off by 1.28% filters from queries that have reached ours.

| Campaign | cpm | volume | impressions | sell-out | revenue |
|---|---|---|---|---|---|
| Bank_24d40196bd94b649 | 280.0 | 22 487 | 22 487 | 100.00% | 6 296 360 |
| Telecom_d46ed517452394a2 | 160.0 | 32 839 | 10 905 | 33.21% | 1 744 800 |
| Retail_59c52779836b2bae | 140.0 | 26 749 | 3 985 | 14.90% | 557 900 |
| Campaign_51288482374d537c | 90.0 | 19 773 | 60 | 0.30% | 5 400 |
| Automotive_9e1edff89ac9a790 | 250.0 | 14 500 | 14 500 | 100.00% | 3 625 000 |
| Campaign_4d4dc901c2e49788 | 200.0 | 28 546 | 28 546 | 100.00% | 5 709 200 |
| Property_5a34d256a53751c3 | 320.0 | 19 352 | 19 352 | 100.00% | 6 192 640 |
| Retail_5d131e8ff2fd6390 | 130.0 | 8 286 | 4 497 | 54.27% | 584 610 |
| Health_0676356d6ba137b6 | 150.0 | 2 927 | 89 | 3.04% | 13 350 |
| Travel_3724963d1920e16a | 200.0 | 3 231 | 2 170 | 67.16% | 434 000 |
| Bank_93461467de106ae8 | 200.0 | 2 882 | 344 | 11.94% | 68 800 |
| Retail_6162b5875d2e4e9b | 130.0 | 5 744 | 1 801 | 31.35% | 234 130 |
| Children_90daa9b022baf620 | 110.0 | 4 208 | 2 840 | 67.49% | 312 400 |
| Children_1aa561689b8b57e7 | 150.0 | 820 | 22 | 2.68% | 3 300 |
| Retail_8846b13f4335d7b7 | 120.0 | 1 394 | 106 | 7.60% | 12 720 |
| Entertainment_69bc7e453450b097 | 170.0 | 1 697 | 203 | 11.96% | 34 510 |
| Entertainment_a1dfc2a1e842d0a2 | 220.0 | 5 796 | 1 381 | 23.83% | 303 820 |
| Entertainment_9237fb2e70bf48fc | 180.0 | 5 248 | 1 782 | 33.96% | 320 760 |
| Campaign_4ada123d5805979b | 100.0 | 2 898 | 1 996 | 68.88% | 199 600 |
| Entertainment_6e3c73f12bc64057 | 90.0 | 1 823 | 30 | 1.65% | 2 700 |
| Retail_de2dbf9477c474eb | 140.0 | 2 548 | 592 | 23.23% | 82 880 |
| Health_f41f5144a75c3d01 | 160.0 | 2 437 | 1 057 | 43.37% | 169 120 |
| Bank_1da9a798e900c021 | 300.0 | 2 891 | 2 891 | 100.00% | 867 300 |
| Automotive_ee52e22a84292a1f | 210.0 | 516 | 153 | 29.65% | 32 130 |
| Campaign_5cb77808ad316b86 | 80.0 | 720 | 49 | 6.81% | 3 920 |
| Campaign_c49a8ec579219c40 | 85.0 | 74 | 0 | 0.00% | 0 |
| Campaign_8bc4330af9c149de | 95.0 | 1 185 | 14 | 1.18% | 1 330 |
| Campaign_e02df8d0c6b01b69 | 60.0 | 57 476 | 1 468 | 2.55% | 88 080 |
| Campaign_2320b836ad0f2d84 | 75.0 | 34 824 | 4 458 | 12.80% | 334 350 |
| Campaign_e5908cfe00510515 | 70.0 | 18 546 | 791 | 4.27% | 55 370 |
| Campaign_ee21aa935c0ed10e | 230.0 | 22 487 | 9 797 | 43.57% | 2 253 310 |
| Campaign_f3fec2802fa06a3c | 230.0 | 22 487 | 11 867 | 52.77% | 2 729 410 |

Hidden Manager Companies (`random`, Diagnostics – The Algorithm Cannot See):

| Campaign | volume | 200 | sell-out |
|---|---|---|---|
| Campaign_4d61f9faeb01d35c | 16 657 | 6 079 | 36.50% |
| Campaign_78f39f90f4505c10 | 23 307 | 10 247 | 43.97% |
| Campaign_0823aa18c3c2ca3c | 5 349 | 2 441 | 45.63% |
| Campaign_bfbd684ea6d38f9c | 23 594 | 11 264 | 47.74% |
| Campaign_30b60302c20096a3 | 25 007 | 5 216 | 20.86% |
| Campaign_18a033858fcef7cd | 607 | 162 | 26.69% |
| Children_b0f1e3ceb0b3da30 | 581 | 92 | 15.83% |
| Campaign_15cc393e200b3c64 | 3 206 | 1 193 | 37.21% |
| Campaign_a16460025af591cd | 6 870 | 945 | 13.76% |
| Campaign_82eaaf51f6f9f1de | 8 721 | 2 057 | 23.59% |
| Campaign_b3953d44c96cf68e | 65 531 | 11 867 | 18.11% |
