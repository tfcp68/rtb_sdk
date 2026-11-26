# Rebuilding Hidden Campaigns

Input algorithms: query features, time, user, 200/204. Winners and seller configuration are used only in the evaluation.

Train: 89,464; test: 29,998. Time breakdown; auction is not reset at the border.

IoU targeting is weighted by profile frequencies **only sent test queries**. Campaign matching: greedy mutually unambiguous at IoU ≥ 0.5.Recall includes campaigns without impressions; outside of test traffic, targeting is not checked.

Campaigns with the same observed behavior are unidentifiable. Rules found are hypotheses: names, CPM, budget, exact frequencies, and flutes are not restored. Cooldown is the total heuristic range of hypotheses, not the min_interval measured real-world campaign.

## Comparison of algorithms

| Algorithm | Hypotheses | Brier ↓ | Logloss ↓ | Accuracy | Precision campaign | Recall campaign | IoU union |
|---|---:|---:|---:|---:|---:|---:|---:|
| single_feature | 12 | 0.1956 | 0.5754 | 0.723 | 0.000 | 0.000 | 0.342 |
| dnf_beam | 6 | 0.1956 | 0.5753 | 0.723 | 0.167 | 0.091 | 0.342 |
| dnf_cooldown_fsm | 6 | 0.1956 | 0.5753 | 0.723 | 0.167 | 0.091 | 0.342 |

The constant (share of 200 in train): Brier=0.2498, Logloss=0.6927.

Static models don't use test responses. FSM first produces a prediction, then receives the actual 200/204 for the next query. FSM parameters are selected on the inner tail of the train; the initial test state is heated by the train history.

## Real and Restored Targeting

Each line has a real campaign, next to each algorithm's closest hypothesis with numbers from the prediction sections and the IoU. Each hypothesis is shown at its nearest real campaign, including IoU < 0.5; this does not mean that the campaign is restored. "No immediate hypotheses" means that no hypothesis has chosen this campaign as the nearest one. Empty targeting is shown as "No Limits."

| A real campaign | Real-life targeting | single_feature | dnf_beam | dnf_cooldown_fsm |
|---|---|---|---|---|
| Campaign_ea5f7d580a451649 | `{"Device": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A"], "Region": ["978039453340", "915202053340", "946620753340", "952038632934"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Campaign_1984973edd3946de | `{"Channel": ["952037271457", "965158348951", "952026274912"]}` | № 2: `{"Channel": ["965158348951"]}` (IoU=0.321)<br>№ 3: `{"Channel": ["952037271457"]}` (IoU=0.371)<br>№ 4: `{"Channel": ["952026274912"]}` (IoU=0.308)<br>№ 11: `{"Region": ["936148586443"]}` (IoU=0.019) | № 2: `{"Region": ["936148586443", "925675058069"]}` (IoU=0.021)<br>№ 6: `{"Channel": ["952037271457", "965158348951", "952026274912"]}` (IoU=1.000) | № 2: `{"Region": ["936148586443", "925675058069"]}` (IoU=0.021)<br>№ 6: `{"Channel": ["952037271457", "965158348951", "952026274912"]}` (IoU=1.000) |
| Campaign_99cdede9ce7aa975 | `{"Channel": ["952038842392", "965160024615", "952038318747", "965157930035", "952039366037"], "Device": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A"]}` | № 6: `{"Channel": ["952038842392"]}` (IoU=0.218) | № 5: `{"Channel": ["952038842392", "924619333696", "952074240794", "952074659710"]}` (IoU=0.153) | № 5: `{"Channel": ["952038842392", "924619333696", "952074240794", "952074659710"]}` (IoU=0.153) |
| Campaign_2be6940a55eb7fa0 | `{"Device": ["SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A"]}` | № 1: `{"Device": ["ANDROID_TV_A"]}` (IoU=0.396)<br>№ 5: `{"Device": ["SMART_TV_PLATFORM_A"]}` (IoU=0.101)<br>№ 7: `{"Channel": ["924619333696"]}` (IoU=0.008)<br>№ 12: `{"Region": ["925675058069"]}` (IoU=0.004) | № 3: `{"Device": ["SMART_TV_PLATFORM_A"]}` (IoU=0.101)<br>№ 4: `{"Device": ["ANDROID_TV_A"]}` (IoU=0.396) | № 3: `{"Device": ["SMART_TV_PLATFORM_A"]}` (IoU=0.101)<br>№ 4: `{"Device": ["ANDROID_TV_A"]}` (IoU=0.396) |
| Campaign_9e11981cace96198 | `{"Category": ["937456303809", "937473479365"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Campaign_cf47c19ce9ef3c4d | `{"Device": ["SET_TOP_BOX_A"], "Region": ["925674953340", "936147853340", "967566553340", "946621486443", "982166824201"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Children_6bf1ef19c6c58f11 | `{"Device": ["ANDROID_TV_A"], "Child": ["true"]}` | № 10: `{"Region": ["919962195848"]}` (IoU=0.039) | № 1: `{"Region": ["919962195848"]}` (IoU=0.039) | № 1: `{"Region": ["919962195848"]}` (IoU=0.039) |
| Campaign_d2be11d252e8975a | `{"Region": ["946621486443", "982166824201", "936148481714"], "Device": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Campaign_ddf62e380a1dc1a3 | `{"Category": ["937473688823", "961393278034"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Campaign_924ddc03b0454da6 | `{"Device": ["ANDROID_TV_A"], "Region": ["978039453340", "915202053340", "946620753340", "952038632934", "925674953340", "936147853340", "967566553340", "946621486443", "982166824201", "936148481714"]}` | № 8: `{"Channel": ["952074659710"]}` (IoU=0.011)<br>№ 9: `{"Channel": ["952074240794"]}` (IoU=0.010) | No nearby hypotheses | No nearby hypotheses |
| Campaign_e8fc9f0e665e7017 | `{"Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A", "ANDROID_TV_A"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |

## What was inside.

- **Campaign_ea5f7d580a451649**: targeting `{"Device": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A"], "Region": ["978039453340", "915202053340", "946620753340", "952038632934"]}`; impressions train/test=3981/1354; plan=9812; min_interval=30; user limits=[[15, 86400], [52, 604800]]; ad limits=[[64, 600], [256, 3600], [3987, 86400]]; flight=0…1152921504606846976 s.
- **Campaign_1984973edd3946de**: targeting `{"Channel": ["952037271457", "965158348951", "952026274912"]}`; impressions train/test=6587/2200; plan=13730; min_interval=20; user limits=[[21, 86400], [67, 604800]]; ad limits=[[626, 3600], [7724, 86400]]; flight=0…1152921504606846976 s.
- **Campaign_99cdede9ce7aa975**: targeting `{"Channel": ["952038842392", "965160024615", "952038318747", "965157930035", "952039366037"], "Device": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A"]}`; impressions train/test=1605/524; plan=3151; min_interval=30; user limits=[[12, 86400], [37, 604800]]; ad limits=[[21, 600], [83, 3600], [1281, 86400]]; flight=0…1152921504606846976 s.
- **Campaign_2be6940a55eb7fa0**: targeting `{"Device": ["SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A"]}`; impressions train/test=18903/5825; plan=48485; min_interval=30; user limits=[[12, 86400], [37, 604800]]; ad limits=[[316, 600], [1263, 3600], [19698, 86400]]; flight=0…1152921504606846976 s.
- **Campaign_9e11981cace96198**: targeting `{"Category": ["937456303809", "937473479365"]}`; impressions train/test=3381/1181; plan=14731; min_interval=60; user limits=[[9, 86400], [30, 604800]]; ad limits=[[96, 600], [384, 3600], [5985, 86400]]; flight=0…1152921504606846976 s.
- **Campaign_cf47c19ce9ef3c4d**: targeting `{"Device": ["SET_TOP_BOX_A"], "Region": ["925674953340", "936147853340", "967566553340", "946621486443", "982166824201"]}`; impressions train/test=97/42; plan=358; min_interval=60; user limits=[[7, 86400], [22, 604800]]; ad limits=[[2, 600], [7, 3600], [124, 86400], [807, 604800]]; flight=0…1152921504606846976 s.
- **Children_6bf1ef19c6c58f11**: targeting `{"Device": ["ANDROID_TV_A"], "Child": ["true"]}`; impressions train/test=66/17; plan=342; min_interval=120; user limits=[[4, 86400], [15, 604800]]; ad limits=[[2, 600], [7, 3600], [118, 86400], [771, 604800]]; flight=0…1152921504606846976 s.
- **Campaign_d2be11d252e8975a**: targeting `{"Region": ["946621486443", "982166824201", "936148481714"], "Device": ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A"]}`; impressions train/test=781/269; plan=1889; min_interval=30; user limits=[[9, 86400], [30, 604800]]; ad limits=[[13, 600], [50, 3600], [768, 86400]]; flight=0…1152921504606846976 s.
- **Campaign_ddf62e380a1dc1a3**: targeting `{"Category": ["937473688823", "961393278034"]}`; impressions train/test=812/0; plan=4047; min_interval=15; user limits=[[15, 86400], [45, 604800]]; ad limits=[[185, 3600], [2277, 86400]]; flight=138240…241919 s.
- **Campaign_924ddc03b0454da6**: targeting `{"Device": ["ANDROID_TV_A"], "Region": ["978039453340", "915202053340", "946620753340", "952038632934", "925674953340", "936147853340", "967566553340", "946621486443", "982166824201", "936148481714"]}`; impressions train/test=383/158; plan=5138; min_interval=30; user limits=[[12, 86400], [37, 604800]]; ad limits=[[34, 600], [134, 3600], [2088, 86400]]; flight=0…1152921504606846976 s.
- **Campaign_e8fc9f0e665e7017**: targeting `{"Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A", "ANDROID_TV_A"]}`; impressions train/test=7624/2803; plan=53774; min_interval=45; user limits=[[7, 86400], [27, 604800]]; ad limits=[[257, 600], [1051, 3600], [18485, 86400], [121160, 604800]]; flight=0…1152921504606846976 s.

## single_feature predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Device": ["ANDROID_TV_A"]}` | 0.816 | 20085 / 16385 | 0 | Campaign_2be6940a55eb7fa0 | 0.396 |
| 2 | `{"Channel": ["965158348951"]}` | 0.969 | 2317 / 2247 | 0 | Campaign_1984973edd3946de | 0.321 |
| 3 | `{"Channel": ["952037271457"]}` | 0.956 | 2745 / 2625 | 0 | Campaign_1984973edd3946de | 0.371 |
| 4 | `{"Channel": ["952026274912"]}` | 0.963 | 2234 / 2153 | 0 | Campaign_1984973edd3946de | 0.308 |
| 5 | `{"Device": ["SMART_TV_PLATFORM_A"]}` | 0.756 | 4647 / 3514 | 0 | Campaign_2be6940a55eb7fa0 | 0.101 |
| 6 | `{"Channel": ["952038842392"]}` | 0.889 | 763 / 679 | 0 | Campaign_99cdede9ce7aa975 | 0.218 |
| 7 | `{"Channel": ["924619333696"]}` | 0.889 | 432 / 385 | 0 | Campaign_2be6940a55eb7fa0 | 0.008 |
| 8 | `{"Channel": ["952074659710"]}` | 0.903 | 359 / 325 | 0 | Campaign_924ddc03b0454da6 | 0.011 |
| 9 | `{"Channel": ["952074240794"]}` | 0.896 | 382 / 343 | 0 | Campaign_924ddc03b0454da6 | 0.010 |
| 10 | `{"Region": ["919962195848"]}` | 0.814 | 267 / 218 | 0 | Children_6bf1ef19c6c58f11 | 0.039 |
| 11 | `{"Region": ["936148586443"]}` | 0.990 | 301 / 299 | 0 | Campaign_1984973edd3946de | 0.019 |
| 12 | `{"Region": ["925675058069"]}` | 0.965 | 198 / 192 | 0 | Campaign_2be6940a55eb7fa0 | 0.004 |

## dnf_beam predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["919962195848"]}` | 0.814 | 267 / 218 | 0 | Children_6bf1ef19c6c58f11 | 0.039 |
| 2 | `{"Region": ["936148586443", "925675058069"]}` | 0.982 | 499 / 491 | 0 | Campaign_1984973edd3946de | 0.021 |
| 3 | `{"Device": ["SMART_TV_PLATFORM_A"]}` | 0.756 | 4647 / 3514 | 0 | Campaign_2be6940a55eb7fa0 | 0.101 |
| 4 | `{"Device": ["ANDROID_TV_A"]}` | 0.816 | 20085 / 16385 | 0 | Campaign_2be6940a55eb7fa0 | 0.396 |
| 5 | `{"Channel": ["952038842392", "924619333696", "952074240794", "952074659710"]}` | 0.894 | 1936 / 1732 | 0 | Campaign_99cdede9ce7aa975 | 0.153 |
| 6 | `{"Channel": ["952037271457", "965158348951", "952026274912"]}` | 0.963 | 7296 / 7025 | 0 | Campaign_1984973edd3946de | 1.000 |

## dnf_cooldown_fsm predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["919962195848"]}` | 0.814 | 267 / 218 | 0 | Children_6bf1ef19c6c58f11 | 0.039 |
| 2 | `{"Region": ["936148586443", "925675058069"]}` | 0.982 | 499 / 491 | 0 | Campaign_1984973edd3946de | 0.021 |
| 3 | `{"Device": ["SMART_TV_PLATFORM_A"]}` | 0.756 | 4647 / 3514 | 0 | Campaign_2be6940a55eb7fa0 | 0.101 |
| 4 | `{"Device": ["ANDROID_TV_A"]}` | 0.816 | 20085 / 16385 | 0 | Campaign_2be6940a55eb7fa0 | 0.396 |
| 5 | `{"Channel": ["952038842392", "924619333696", "952074240794", "952074659710"]}` | 0.894 | 1936 / 1732 | 0 | Campaign_99cdede9ce7aa975 | 0.153 |
| 6 | `{"Channel": ["952037271457", "965158348951", "952026274912"]}` | 0.963 | 7296 / 7025 | 0 | Campaign_1984973edd3946de | 1.000 |
