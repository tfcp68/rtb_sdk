# Open run of `demo`

Parameters: {"sample": 0.05834053566692987, "q": 0.8, "policy": "random", "pool_devices": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "days": [0, 4], "seed": 42, "manager_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/manager_ads.json", "our_ads": "/home/gnevich/auction_platform/benchmarks/closed_stand/../log_benchmark/ads_manual.json", "manager_price": 150.0, "fallback_204": false}

### Open run (learning log)

| Politics | Days | Sent / pool | Sent / traffic | Sell-through (200/gone) | 200 / pool | 200 piece | Manager’s revenue | Revenue from ours | Total |
|---|---|---|---|---|---|---|---|---|---|
| random | 0:4 | 80.01% | 49.52% | 38.35% | 30.68% | 940 342 | 141 051 300 | 514 680 645 | 655 731 945 |

Relative to `random` (same volume):

#### `random` - by day

| Day | Requests | Pool | Sent | Sent/pool | 200 | Sell-through |
|---|---|---|---|---|---|---|
| 0 | 1 132 799 | 664 742 | 531 929 | 80.02% | 222 509 | 41.83% |
| 1 | 1 166 132 | 708 767 | 567 058 | 80.01% | 227 085 | 40.05% |
| 2 | 1 291 739 | 815 949 | 652 889 | 80.02% | 244 926 | 37.51% |
| 3 | 1 361 005 | 875 397 | 700 171 | 79.98% | 245 822 | 35.11% |

Our companies (`random`): sold 2 436 976 impressions, without targeting 0.00%, cut off by 2.51% filters from queries that have reached ours.

| Campaign | cpm | volume | impressions | sell-out | revenue |
|---|---|---|---|---|---|
| Bank_24d40196bd94b649 | 280.0 | 359 857 | 359 857 | 100.00% | 100 759 960 |
| Telecom_d46ed517452394a2 | 160.0 | 669 695 | 284 893 | 42.54% | 45 582 880 |
| Retail_59c52779836b2bae | 140.0 | 518 603 | 115 706 | 22.31% | 16 198 840 |
| Campaign_51288482374d537c | 90.0 | 342 865 | 3 441 | 1.00% | 309 690 |
| Automotive_9e1edff89ac9a790 | 250.0 | 299 349 | 299 349 | 100.00% | 74 837 250 |
| Campaign_4d4dc901c2e49788 | 200.0 | 405 015 | 258 945 | 63.93% | 51 789 000 |
| Property_5a34d256a53751c3 | 320.0 | 164 339 | 164 339 | 100.00% | 52 588 480 |
| Retail_5d131e8ff2fd6390 | 130.0 | 129 499 | 64 977 | 50.18% | 8 447 010 |
| Health_0676356d6ba137b6 | 150.0 | 76 062 | 3 258 | 4.28% | 488 700 |
| Travel_3724963d1920e16a | 200.0 | 85 991 | 63 208 | 73.51% | 12 641 600 |
| Bank_93461467de106ae8 | 200.0 | 77 843 | 3 288 | 4.22% | 657 600 |
| Retail_6162b5875d2e4e9b | 130.0 | 97 816 | 46 146 | 47.18% | 5 998 980 |
| Children_90daa9b022baf620 | 110.0 | 23 651 | 10 712 | 45.29% | 1 178 320 |
| Children_1aa561689b8b57e7 | 150.0 | 5 897 | 764 | 12.96% | 114 600 |
| Retail_8846b13f4335d7b7 | 120.0 | 38 779 | 5 252 | 13.54% | 630 240 |
| Entertainment_69bc7e453450b097 | 170.0 | 45 701 | 6 898 | 15.09% | 1 172 660 |
| Entertainment_a1dfc2a1e842d0a2 | 220.0 | 186 838 | 106 274 | 56.88% | 23 380 280 |
| Entertainment_9237fb2e70bf48fc | 180.0 | 81 657 | 49 143 | 60.18% | 8 845 740 |
| Campaign_4ada123d5805979b | 100.0 | 43 425 | 43 425 | 100.00% | 4 342 500 |
| Entertainment_6e3c73f12bc64057 | 90.0 | 13 977 | 4 192 | 29.99% | 377 280 |
| Retail_de2dbf9477c474eb | 140.0 | 44 165 | 10 405 | 23.56% | 1 456 700 |
| Health_f41f5144a75c3d01 | 160.0 | 27 107 | 17 120 | 63.16% | 2 739 200 |
| Bank_1da9a798e900c021 | 300.0 | 84 431 | 84 431 | 100.00% | 25 329 300 |
| Automotive_ee52e22a84292a1f | 210.0 | 13 031 | 5 122 | 39.31% | 1 075 620 |
| Campaign_5cb77808ad316b86 | 80.0 | 19 599 | 2 514 | 12.83% | 201 120 |
| Campaign_c49a8ec579219c40 | 85.0 | 3 732 | 391 | 10.48% | 33 235 |
| Campaign_8bc4330af9c149de | 95.0 | 30 747 | 256 | 0.83% | 24 320 |
| Campaign_e02df8d0c6b01b69 | 60.0 | 935 674 | 50 393 | 5.39% | 3 023 580 |
| Campaign_2320b836ad0f2d84 | 75.0 | 579 572 | 71 666 | 12.37% | 5 374 950 |
| Campaign_e5908cfe00510515 | 70.0 | 312 549 | 25 372 | 8.12% | 1 776 040 |
| Campaign_ee21aa935c0ed10e | 230.0 | 359 857 | 99 886 | 27.76% | 22 973 780 |
| Campaign_f3fec2802fa06a3c | 230.0 | 359 857 | 175 353 | 48.73% | 40 331 190 |

Hidden Manager Companies (`random`, Diagnostics – The Algorithm Cannot See):

| Campaign | volume | 200 | sell-out |
|---|---|---|---|
| Campaign_4d61f9faeb01d35c | 338 075 | 109 218 | 32.31% |
| Campaign_78f39f90f4505c10 | 322 435 | 268 486 | 83.27% |
| Campaign_0823aa18c3c2ca3c | 115 149 | 70 877 | 61.55% |
| Campaign_bfbd684ea6d38f9c | 413 689 | 180 028 | 43.52% |
| Campaign_30b60302c20096a3 | 300 486 | 45 272 | 15.07% |
| Campaign_18a033858fcef7cd | 27 946 | 4 806 | 17.20% |
| Children_b0f1e3ceb0b3da30 | 20 885 | 2 272 | 10.88% |
| Campaign_15cc393e200b3c64 | 107 876 | 28 858 | 26.75% |
| Campaign_a16460025af591cd | 81 414 | 7 342 | 9.02% |
| Campaign_82eaaf51f6f9f1de | 295 039 | 56 519 | 19.16% |
| Campaign_b3953d44c96cf68e | 1 164 456 | 166 664 | 14.31% |
