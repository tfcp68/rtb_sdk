# Open run of `shtuka`

Parameters: {"sample": 0.03809057377751046, "q": 0.8, "policy": "random", "pool_devices": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "days": [0, 4], "seed": 42, "prepared_signature": "8d878284379be2535b0445785f09ebecfda7c718308eb51ed2df9c4ec8ee5a81", "prepared_source": "/home/gnevich/auction_platform/benchmarks/log_benchmark/../logs/janus_20261012_20261019.parquet", "manager_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/manager_target50_20261012.json", "our_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/../log_benchmark/ads_manual.json", "manager_price": 150.0, "fallback_204": false}

### Open run (learning log)

| Politics | Days | Sent / pool | Sent / traffic | Sell-through (200/gone) | 200 / pool | 200 piece | Manager’s revenue | Revenue from ours | Total |
|---|---|---|---|---|---|---|---|---|---|
| random | 0:4 | 80.01% | 46.56% | 49.49% | 39.60% | 1 144 818 | 171 722 700 | 577 728 605 | 749 451 305 |

Relative to `random` (same volume):

#### `random` - by day

| Day | Requests | Pool | Sent | Sent/pool | 200 | Sell-through |
|---|---|---|---|---|---|---|
| 0 | 1 220 936 | 717 723 | 574 375 | 80.03% | 289 361 | 50.38% |
| 1 | 1 339 257 | 727 342 | 581 534 | 79.95% | 287 008 | 49.35% |
| 2 | 1 279 750 | 733 398 | 587 438 | 80.10% | 290 774 | 49.50% |
| 3 | 1 127 594 | 712 580 | 569 750 | 79.96% | 277 675 | 48.74% |

Our companies (`random`): sold 2 618 797 impressions, without targeting 0.00%, cut off by 1.34% filters from queries that have reached ours.

| Campaign | cpm | volume | impressions | sell-out | revenue |
|---|---|---|---|---|---|
| Bank_24d40196bd94b649 | 280.0 | 384 786 | 384 786 | 100.00% | 107 740 080 |
| Telecom_d46ed517452394a2 | 160.0 | 561 924 | 187 629 | 33.39% | 30 020 640 |
| Retail_59c52779836b2bae | 140.0 | 457 716 | 75 064 | 16.40% | 10 508 960 |
| Campaign_51288482374d537c | 90.0 | 338 355 | 2 243 | 0.66% | 201 870 |
| Automotive_9e1edff89ac9a790 | 250.0 | 248 126 | 248 126 | 100.00% | 62 031 500 |
| Campaign_4d4dc901c2e49788 | 200.0 | 488 480 | 488 480 | 100.00% | 97 696 000 |
| Property_5a34d256a53751c3 | 320.0 | 331 143 | 331 143 | 100.00% | 105 965 760 |
| Retail_5d131e8ff2fd6390 | 130.0 | 141 784 | 77 014 | 54.32% | 10 011 820 |
| Health_0676356d6ba137b6 | 150.0 | 50 085 | 1 381 | 2.76% | 207 150 |
| Travel_3724963d1920e16a | 200.0 | 55 282 | 37 143 | 67.19% | 7 428 600 |
| Bank_93461467de106ae8 | 200.0 | 49 316 | 4 591 | 9.31% | 918 200 |
| Retail_6162b5875d2e4e9b | 130.0 | 98 288 | 29 505 | 30.02% | 3 835 650 |
| Children_90daa9b022baf620 | 110.0 | 72 005 | 47 929 | 66.56% | 5 272 190 |
| Children_1aa561689b8b57e7 | 150.0 | 14 027 | 600 | 4.28% | 90 000 |
| Retail_8846b13f4335d7b7 | 120.0 | 23 852 | 1 484 | 6.22% | 178 080 |
| Entertainment_69bc7e453450b097 | 170.0 | 29 036 | 3 080 | 10.61% | 523 600 |
| Entertainment_a1dfc2a1e842d0a2 | 220.0 | 99 184 | 28 299 | 28.53% | 6 225 780 |
| Entertainment_9237fb2e70bf48fc | 180.0 | 89 807 | 34 554 | 38.48% | 6 219 720 |
| Campaign_4ada123d5805979b | 100.0 | 49 589 | 36 124 | 72.85% | 3 612 400 |
| Entertainment_6e3c73f12bc64057 | 90.0 | 31 202 | 1 879 | 6.02% | 169 110 |
| Retail_de2dbf9477c474eb | 140.0 | 43 599 | 14 589 | 33.46% | 2 042 460 |
| Health_f41f5144a75c3d01 | 160.0 | 41 709 | 19 394 | 46.50% | 3 103 040 |
| Bank_1da9a798e900c021 | 300.0 | 49 468 | 49 468 | 100.00% | 14 840 400 |
| Automotive_ee52e22a84292a1f | 210.0 | 8 829 | 2 583 | 29.26% | 542 430 |
| Campaign_5cb77808ad316b86 | 80.0 | 12 315 | 1 775 | 14.41% | 142 000 |
| Campaign_c49a8ec579219c40 | 85.0 | 1 273 | 73 | 5.73% | 6 205 |
| Campaign_8bc4330af9c149de | 95.0 | 20 280 | 121 | 0.60% | 11 495 |
| Campaign_e02df8d0c6b01b69 | 60.0 | 983 511 | 28 722 | 2.92% | 1 723 320 |
| Campaign_2320b836ad0f2d84 | 75.0 | 595 905 | 74 033 | 12.42% | 5 552 475 |
| Campaign_e5908cfe00510515 | 70.0 | 317 349 | 16 868 | 5.32% | 1 180 760 |
| Campaign_ee21aa935c0ed10e | 230.0 | 384 786 | 176 860 | 45.96% | 40 677 800 |
| Campaign_f3fec2802fa06a3c | 230.0 | 384 786 | 213 257 | 55.42% | 49 049 110 |

Hidden Manager Companies (`random`, Diagnostics – The Algorithm Cannot See):

| Campaign | volume | 200 | sell-out |
|---|---|---|---|
| Campaign_4d61f9faeb01d35c | 189 782 | 107 770 | 56.79% |
| Campaign_78f39f90f4505c10 | 265 552 | 172 590 | 64.99% |
| Campaign_0823aa18c3c2ca3c | 60 949 | 41 766 | 68.53% |
| Campaign_bfbd684ea6d38f9c | 937 743 | 471 644 | 50.30% |
| Campaign_30b60302c20096a3 | 284 914 | 91 049 | 31.96% |
| Campaign_18a033858fcef7cd | 6 920 | 2 201 | 31.81% |
| Children_b0f1e3ceb0b3da30 | 6 615 | 1 714 | 25.91% |
| Campaign_15cc393e200b3c64 | 36 528 | 22 253 | 60.92% |
| Campaign_a16460025af591cd | 78 276 | 19 279 | 24.63% |
| Campaign_82eaaf51f6f9f1de | 99 368 | 12 086 | 12.16% |
| Campaign_b3953d44c96cf68e | 1 040 037 | 202 466 | 19.47% |
