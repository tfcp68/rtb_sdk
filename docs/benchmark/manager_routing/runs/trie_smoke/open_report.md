# Open run of `trie_smoke`

Parameters: {"sample": 0.0020030594730391198, "q": 0.8, "policy": "random", "pool_devices": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "days": [0, 2], "seed": 42, "manager_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/manager_ads.json", "our_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/../log_benchmark/ads_manual.json", "manager_price": 150.0, "fallback_204": false}

### Open run (learning log)

| Politics | Days | Sent / pool | Sent / traffic | Sell-through (200/gone) | 200 / pool | 200 piece | Manager’s revenue | Revenue from ours | Total |
|---|---|---|---|---|---|---|---|---|---|
| random | 0:2 | 80.15% | 48.30% | 39.52% | 31.68% | 15 386 | 2 307 900 | 8 546 910 | 10 854 810 |

Relative to `random` (same volume):

#### `random` - by day

| Day | Requests | Pool | Sent | Sent/pool | 200 | Sell-through |
|---|---|---|---|---|---|---|
| 0 | 40 750 | 24 254 | 19 443 | 80.16% | 7 711 | 39.66% |
| 1 | 39 851 | 24 313 | 19 485 | 80.14% | 7 675 | 39.39% |

Our companies (`random`): sold 40 312 impressions, without targeting 0.00%, cut off by 3.27% filters from queries that have reached ours.

| Campaign | cpm | volume | impressions | sell-out | revenue |
|---|---|---|---|---|---|
| Bank_24d40196bd94b649 | 280.0 | 5 858 | 5 858 | 100.00% | 1 640 240 |
| Telecom_d46ed517452394a2 | 160.0 | 10 901 | 4 348 | 39.89% | 695 680 |
| Retail_59c52779836b2bae | 140.0 | 8 442 | 1 833 | 21.71% | 256 620 |
| Campaign_51288482374d537c | 90.0 | 5 581 | 0 | 0.00% | 0 |
| Automotive_9e1edff89ac9a790 | 250.0 | 4 873 | 4 873 | 100.00% | 1 218 250 |
| Campaign_4d4dc901c2e49788 | 200.0 | 6 593 | 4 200 | 63.70% | 840 000 |
| Property_5a34d256a53751c3 | 320.0 | 2 675 | 2 675 | 100.00% | 856 000 |
| Retail_5d131e8ff2fd6390 | 130.0 | 2 108 | 1 130 | 53.61% | 146 900 |
| Health_0676356d6ba137b6 | 150.0 | 1 238 | 33 | 2.67% | 4 950 |
| Travel_3724963d1920e16a | 200.0 | 1 400 | 895 | 63.93% | 179 000 |
| Bank_93461467de106ae8 | 200.0 | 1 267 | 29 | 2.29% | 5 800 |
| Retail_6162b5875d2e4e9b | 130.0 | 1 592 | 628 | 39.45% | 81 640 |
| Children_90daa9b022baf620 | 110.0 | 385 | 199 | 51.69% | 21 890 |
| Children_1aa561689b8b57e7 | 150.0 | 96 | 0 | 0.00% | 0 |
| Retail_8846b13f4335d7b7 | 120.0 | 631 | 59 | 9.35% | 7 080 |
| Entertainment_69bc7e453450b097 | 170.0 | 744 | 73 | 9.81% | 12 410 |
| Entertainment_a1dfc2a1e842d0a2 | 220.0 | 3 041 | 2 171 | 71.39% | 477 620 |
| Entertainment_9237fb2e70bf48fc | 180.0 | 1 329 | 746 | 56.13% | 134 280 |
| Campaign_4ada123d5805979b | 100.0 | 707 | 707 | 100.00% | 70 700 |
| Entertainment_6e3c73f12bc64057 | 90.0 | 228 | 42 | 18.42% | 3 780 |
| Retail_de2dbf9477c474eb | 140.0 | 719 | 126 | 17.52% | 17 640 |
| Health_f41f5144a75c3d01 | 160.0 | 441 | 227 | 51.47% | 36 320 |
| Bank_1da9a798e900c021 | 300.0 | 1 374 | 1 374 | 100.00% | 412 200 |
| Automotive_ee52e22a84292a1f | 210.0 | 212 | 87 | 41.04% | 18 270 |
| Campaign_5cb77808ad316b86 | 80.0 | 319 | 50 | 15.67% | 4 000 |
| Campaign_c49a8ec579219c40 | 85.0 | 61 | 2 | 3.28% | 170 |
| Campaign_8bc4330af9c149de | 95.0 | 500 | 0 | 0.00% | 0 |
| Campaign_e02df8d0c6b01b69 | 60.0 | 15 230 | 1 173 | 7.70% | 70 380 |
| Campaign_2320b836ad0f2d84 | 75.0 | 9 434 | 1 046 | 11.09% | 78 450 |
| Campaign_e5908cfe00510515 | 70.0 | 5 088 | 380 | 7.47% | 26 600 |
| Campaign_ee21aa935c0ed10e | 230.0 | 5 858 | 2 010 | 34.31% | 462 300 |
| Campaign_f3fec2802fa06a3c | 230.0 | 5 858 | 3 338 | 56.98% | 767 740 |

Hidden Manager Companies (`random`, Diagnostics – The Algorithm Cannot See):

| Campaign | volume | 200 | sell-out |
|---|---|---|---|
| Campaign_4d61f9faeb01d35c | 5 357 | 1 978 | 36.92% |
| Campaign_78f39f90f4505c10 | 5 109 | 4 268 | 83.54% |
| Campaign_0823aa18c3c2ca3c | 1 825 | 887 | 48.60% |
| Campaign_bfbd684ea6d38f9c | 6 556 | 2 905 | 44.31% |
| Campaign_30b60302c20096a3 | 4 762 | 916 | 19.24% |
| Campaign_18a033858fcef7cd | 443 | 84 | 18.96% |
| Children_b0f1e3ceb0b3da30 | 331 | 46 | 13.90% |
| Campaign_15cc393e200b3c64 | 1 709 | 463 | 27.09% |
| Campaign_a16460025af591cd | 1 290 | 134 | 10.39% |
| Campaign_82eaaf51f6f9f1de | 4 675 | 931 | 19.91% |
| Campaign_b3953d44c96cf68e | 18 453 | 2 774 | 15.03% |
