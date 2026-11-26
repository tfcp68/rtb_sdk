# XGBoost and CatBoost Runs Across Three Seeds

Seeds 43, 44, and 45. Manager routing quotas are 60% and 80% of the eligible pool. The remaining traffic goes to house campaigns.
All runs share the same training log (day slice `0:4`), test on day slice `5:7`, and use epsilon = 0.02. The seed varies only in the closed-stand evaluations.
Profiling with cProfile was disabled. The total_seconds field includes initial model training and simulation. The stand's original simulation timer is stored in result.seconds.
Versions used were XGBoost 3.4.1 and CatBoost 1.2.10.

All 36 evaluations completed.

| Manager quota | Model | n | Sell-through (200 / sent), mean ± SD | Sent / eligible pool, mean | Total revenue, mean | Full evaluation time, mean (s) |
|---|---|---:|---:|---:|---:|---:|
| 60% | xgboost | 3 | 55.878% ± 0.048 pp | 59.956% | 328,676,208 | 200.6 |
| 60% | xgb_fb | 3 | 58.786% ± 0.009 pp | 60.035% | 334,535,090 | 296.3 |
| 60% | xgb_user | 3 | 58.793% ± 0.017 pp | 60.113% | 330,756,300 | 369.6 |
| 60% | catboost | 3 | 55.751% ± 0.053 pp | 59.926% | 328,010,157 | 524.9 |
| 60% | catboost_fb | 3 | 58.785% ± 0.011 pp | 60.039% | 334,281,902 | 431.2 |
| 60% | catboost_user | 3 | 58.779% ± 0.018 pp | 60.108% | 330,119,950 | 476.2 |
| 80% | xgboost | 3 | 46.287% ± 0.007 pp | 79.961% | 305,884,463 | 205.9 |
| 80% | xgb_fb | 3 | 46.557% ± 0.012 pp | 79.982% | 305,843,842 | 303.9 |
| 80% | xgb_user | 3 | 46.493% ± 0.011 pp | 80.043% | 304,444,310 | 366.5 |
| 80% | catboost | 3 | 46.277% ± 0.005 pp | 79.905% | 305,838,258 | 537.7 |
| 80% | catboost_fb | 3 | 46.575% ± 0.015 pp | 79.949% | 304,969,333 | 465.9 |
| 80% | catboost_user | 3 | 46.486% ± 0.009 pp | 80.046% | 303,649,058 | 485.8 |

## Results by Evaluation

| Seed | Manager quota | Model | Sell-through (200 / sent) | Sent / eligible pool | 200 responses | Total revenue | Full evaluation time (s) |
|---:|---:|---|---:|---:|---:|---:|---:|
| 43 | 60% | xgboost | 55.8235% | 59.9961% | 474768 | 328,506,580 | 208.4 |
| 43 | 60% | xgb_fb | 58.7928% | 60.0235% | 500250 | 334,617,280 | 370.6 |
| 43 | 60% | xgb_user | 58.7957% | 60.1111% | 501005 | 330,830,815 | 382.6 |
| 43 | 60% | catboost | 55.7858% | 59.9152% | 473808 | 328,080,815 | 531.3 |
| 43 | 60% | catboost_fb | 58.7740% | 60.0397% | 500225 | 334,285,175 | 465.5 |
| 43 | 60% | catboost_user | 58.7641% | 60.1117% | 500741 | 330,117,870 | 499.0 |
| 43 | 80% | xgboost | 46.2900% | 79.9587% | 524681 | 305,896,925 | 239.4 |
| 43 | 80% | xgb_fb | 46.5581% | 79.9806% | 527864 | 305,809,790 | 389.9 |
| 43 | 80% | xgb_user | 46.4899% | 80.0438% | 527507 | 304,532,825 | 376.4 |
| 43 | 80% | catboost | 46.2827% | 79.9052% | 524246 | 305,858,330 | 563.4 |
| 43 | 80% | catboost_fb | 46.5726% | 79.9546% | 527856 | 304,880,455 | 471.0 |
| 43 | 80% | catboost_user | 46.4959% | 80.0330% | 527503 | 303,617,220 | 531.8 |
| 44 | 60% | xgboost | 55.9045% | 59.9487% | 475082 | 328,661,405 | 203.8 |
| 44 | 60% | xgb_fb | 58.7764% | 60.0491% | 500324 | 334,478,685 | 251.2 |
| 44 | 60% | xgb_user | 58.8087% | 60.1097% | 501104 | 330,686,375 | 371.6 |
| 44 | 60% | catboost | 55.6909% | 59.9281% | 473104 | 327,968,285 | 535.9 |
| 44 | 60% | catboost_fb | 58.7958% | 60.0388% | 500403 | 334,384,145 | 426.4 |
| 44 | 60% | catboost_user | 58.7987% | 60.0922% | 500873 | 330,217,205 | 471.3 |
| 44 | 80% | xgboost | 46.2925% | 79.9613% | 524726 | 305,809,600 | 181.4 |
| 44 | 80% | xgb_fb | 46.5688% | 79.9631% | 527870 | 305,818,760 | 249.9 |
| 44 | 80% | xgb_user | 46.5049% | 80.0240% | 527546 | 304,515,885 | 364.8 |
| 44 | 80% | catboost | 46.2773% | 79.8906% | 524090 | 305,741,315 | 543.1 |
| 44 | 80% | catboost_fb | 46.5903% | 79.9202% | 527830 | 305,005,250 | 522.0 |
| 44 | 80% | catboost_user | 46.4806% | 80.0484% | 527432 | 303,656,710 | 469.4 |
| 45 | 60% | xgboost | 55.9072% | 59.9219% | 474892 | 328,860,640 | 189.6 |
| 45 | 60% | xgb_fb | 58.7889% | 60.0319% | 500287 | 334,509,305 | 267.1 |
| 45 | 60% | xgb_user | 58.7746% | 60.1196% | 500896 | 330,751,710 | 354.6 |
| 45 | 60% | catboost | 55.7774% | 59.9344% | 473889 | 327,981,370 | 507.6 |
| 45 | 60% | catboost_fb | 58.7849% | 60.0374% | 500299 | 334,176,385 | 401.8 |
| 45 | 60% | catboost_user | 58.7740% | 60.1187% | 500883 | 330,024,775 | 458.3 |
| 45 | 80% | xgboost | 46.2790% | 79.9642% | 524592 | 305,946,865 | 197.0 |
| 45 | 80% | xgb_fb | 46.5455% | 80.0027% | 527866 | 305,902,975 | 271.7 |
| 45 | 80% | xgb_user | 46.4842% | 80.0605% | 527552 | 304,284,220 | 358.5 |
| 45 | 80% | catboost | 46.2723% | 79.9204% | 524229 | 305,915,130 | 506.7 |
| 45 | 80% | catboost_fb | 46.5607% | 79.9717% | 527834 | 305,022,295 | 404.5 |
| 45 | 80% | catboost_user | 46.4817% | 80.0572% | 527502 | 303,673,245 | 456.4 |

SD is the sample standard deviation across seeds, in percentage points (pp). The three seeds give a preliminary estimate of variability with the same test period and training log.
