# Open run of `new_source_smoke`

Parameters: {"sample": 0.0011815843637278235, "q": 0.8, "policy": "random", "pool_devices": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "days": [0, 2], "seed": 42, "prepared_signature": "8d878284379be2535b0445785f09ebecfda7c718308eb51ed2df9c4ec8ee5a81", "prepared_source": "/home/gnevich/auction_platform/benchmarks/log_benchmark/../logs/janus_20261012_20261019.parquet", "manager_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/manager_ads.json", "our_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/../log_benchmark/ads_manual.json", "manager_price": 150.0, "fallback_204": false}

### Open run (learning log)

| Politics | Days | Sent / pool | Sent / traffic | Sell-through (200/gone) | 200 / pool | 200 piece | Manager’s revenue | Revenue from ours | Total |
|---|---|---|---|---|---|---|---|---|---|
| random | 0:2 | 80.19% | 46.05% | 32.60% | 26.14% | 11 914 | 1 787 100 | 9 196 435 | 10 983 535 |

Relative to `random` (same volume):

#### `random` - by day

| Day | Requests | Pool | Sent | Sent/pool | 200 | Sell-through |
|---|---|---|---|---|---|---|
| 0 | 38 214 | 22 760 | 18 247 | 80.17% | 6 182 | 33.88% |
| 1 | 41 147 | 22 817 | 18 301 | 80.21% | 5 732 | 31.32% |

Our companies (`random`): sold 42 061 impressions, without targeting 0.00%, cut off by 1.76% filters from queries that have reached ours.

| Campaign | cpm | volume | impressions | sell-out | revenue |
|---|---|---|---|---|---|
| Bank_24d40196bd94b649 | 280.0 | 6 147 | 6 147 | 100.00% | 1 721 160 |
| Telecom_d46ed517452394a2 | 160.0 | 8 977 | 3 688 | 41.08% | 590 080 |
| Retail_59c52779836b2bae | 140.0 | 7 312 | 2 083 | 28.49% | 291 620 |
| Campaign_51288482374d537c | 90.0 | 5 406 | 43 | 0.80% | 3 870 |
| Automotive_9e1edff89ac9a790 | 250.0 | 3 964 | 3 964 | 100.00% | 991 000 |
| Campaign_4d4dc901c2e49788 | 200.0 | 7 804 | 7 804 | 100.00% | 1 560 800 |
| Property_5a34d256a53751c3 | 320.0 | 5 290 | 5 290 | 100.00% | 1 692 800 |
| Retail_5d131e8ff2fd6390 | 130.0 | 2 265 | 1 091 | 48.17% | 141 830 |
| Health_0676356d6ba137b6 | 150.0 | 800 | 31 | 3.88% | 4 650 |
| Travel_3724963d1920e16a | 200.0 | 883 | 552 | 62.51% | 110 400 |
| Bank_93461467de106ae8 | 200.0 | 788 | 115 | 14.59% | 23 000 |
| Retail_6162b5875d2e4e9b | 130.0 | 1 570 | 522 | 33.25% | 67 860 |
| Children_90daa9b022baf620 | 110.0 | 1 150 | 703 | 61.13% | 77 330 |
| Children_1aa561689b8b57e7 | 150.0 | 224 | 8 | 3.57% | 1 200 |
| Retail_8846b13f4335d7b7 | 120.0 | 381 | 26 | 6.82% | 3 120 |
| Entertainment_69bc7e453450b097 | 170.0 | 464 | 59 | 12.72% | 10 030 |
| Entertainment_a1dfc2a1e842d0a2 | 220.0 | 1 585 | 429 | 27.07% | 94 380 |
| Entertainment_9237fb2e70bf48fc | 180.0 | 1 435 | 444 | 30.94% | 79 920 |
| Campaign_4ada123d5805979b | 100.0 | 792 | 643 | 81.19% | 64 300 |
| Entertainment_6e3c73f12bc64057 | 90.0 | 498 | 30 | 6.02% | 2 700 |
| Retail_de2dbf9477c474eb | 140.0 | 697 | 184 | 26.40% | 25 760 |
| Health_f41f5144a75c3d01 | 160.0 | 666 | 249 | 37.39% | 39 840 |
| Bank_1da9a798e900c021 | 300.0 | 790 | 790 | 100.00% | 237 000 |
| Automotive_ee52e22a84292a1f | 210.0 | 141 | 31 | 21.99% | 6 510 |
| Campaign_5cb77808ad316b86 | 80.0 | 197 | 21 | 10.66% | 1 680 |
| Campaign_c49a8ec579219c40 | 85.0 | 20 | 1 | 5.00% | 85 |
| Campaign_8bc4330af9c149de | 95.0 | 324 | 0 | 0.00% | 0 |
| Campaign_e02df8d0c6b01b69 | 60.0 | 15 712 | 461 | 2.93% | 27 660 |
| Campaign_2320b836ad0f2d84 | 75.0 | 9 520 | 1 066 | 11.20% | 79 950 |
| Campaign_e5908cfe00510515 | 70.0 | 5 070 | 243 | 4.79% | 17 010 |
| Campaign_ee21aa935c0ed10e | 230.0 | 6 147 | 1 849 | 30.08% | 425 270 |
| Campaign_f3fec2802fa06a3c | 230.0 | 6 147 | 3 494 | 56.84% | 803 620 |

Hidden Manager Companies (`random`, Diagnostics – The Algorithm Cannot See):

| Campaign | volume | 200 | sell-out |
|---|---|---|---|
| Campaign_4d61f9faeb01d35c | 5 012 | 1 455 | 29.03% |
| Campaign_78f39f90f4505c10 | 2 718 | 2 499 | 91.94% |
| Campaign_0823aa18c3c2ca3c | 993 | 620 | 62.44% |
| Campaign_bfbd684ea6d38f9c | 5 425 | 2 465 | 45.44% |
| Campaign_30b60302c20096a3 | 7 524 | 1 132 | 15.05% |
| Campaign_18a033858fcef7cd | 183 | 38 | 20.77% |
| Children_b0f1e3ceb0b3da30 | 175 | 30 | 17.14% |
| Campaign_15cc393e200b3c64 | 965 | 273 | 28.29% |
| Campaign_a16460025af591cd | 2 067 | 240 | 11.61% |
| Campaign_82eaaf51f6f9f1de | 2 624 | 511 | 19.47% |
| Campaign_b3953d44c96cf68e | 19 716 | 2 651 | 13.45% |
