# Rebuilding Hidden Campaigns

Input algorithms: query features, time, user, 200/204. Winners and seller configuration are used only in the evaluation.

Train: 620,276; test: 487,867. Time breakdown; auction is not reset at the border.

IoU targeting is weighted by profile frequencies **only sent test queries**. Campaign matching: greedy mutually unambiguous at IoU ≥ 0.5.Recall includes campaigns without impressions; outside of test traffic, targeting is not checked.

Campaigns with the same observed behavior are unidentifiable. Rules found are hypotheses: names, CPM, budget, exact frequencies, and flutes are not restored. Cooldown is the total heuristic range of hypotheses, not the min_interval measured real-world campaign.

motif_noisy_or: P(200)=1−(1−background)∏(1−activation) coincidentally. In his table P(200) indicates the probability of activation of a particular motif, Not the full probability of a response when crossing the rules.

## Comparison of algorithms

| Algorithm | Hypotheses | Brier ↓ | Logloss ↓ | Accuracy | Precision campaign | Recall campaign | IoU union |
|---|---:|---:|---:|---:|---:|---:|---:|
| single_feature | 8 | 0.0711 | 0.2573 | 0.921 | 0.625 | 0.625 | 0.808 |
| dnf_beam | 5 | 0.0711 | 0.2573 | 0.921 | 0.800 | 0.500 | 0.808 |
| dnf_cooldown_fsm | 5 | 0.0711 | 0.2573 | 0.921 | 0.800 | 0.500 | 0.808 |
| dnf_validated | 8 | 0.0484 | 0.1738 | 0.928 | 0.750 | 0.750 | 0.843 |
| motif_noisy_or | 7 | 0.0024 | 0.0098 | 0.997 | 1.000 | 0.875 | 0.994 |

The constant (share of 200 in train): Brier=0.2410, Logloss=0.6750.

Static models don't use test responses. FSM first produces a prediction, then receives the actual 200/204 for the next query. FSM parameters are selected on the inner tail of the train; the initial test state is heated by the train history.

## Real and Restored Targeting

Each line has a real campaign, next to each algorithm's closest hypothesis with numbers from the prediction sections and the IoU. Each hypothesis is shown at its nearest real campaign, including IoU < 0.5; this does not mean that the campaign is restored. "No immediate hypotheses" means that no hypothesis has chosen this campaign as the nearest one. Empty targeting is shown as "No Limits."

| A real campaign | Real-life targeting | single_feature | dnf_beam | dnf_cooldown_fsm | dnf_validated | motif_noisy_or |
|---|---|---|---|---|---|---|
| Campaign_66064f3dd9c1af0b | `{"Category": ["937456303809"]}` | № 1: `{"Category": ["937456303809"]}` (IoU=1.000) | № 4: `{"Category": ["937456303809", "937708072325", "937461435530"]}` (IoU=0.821) | № 4: `{"Category": ["937456303809", "937708072325", "937461435530"]}` (IoU=0.821) | № 6: `{"Category": ["937456303809", "937708072325", "937461435530"]}` (IoU=0.821) | № 6: `{"Category": ["937456303809", "937708072325", "937461435530"]}` (IoU=0.821) |
| Campaign_e0698aae09dcee95 | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "Child": ["false", "true"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 3: `{"Region": ["939929993546"], "Child": ["false"]}` (IoU=0.000)<br>№ 4: `{"Device": ["SMART_TV_PLATFORM_C"], "Child": ["false"]}` (IoU=0.828) | № 4: `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "Child": ["false", "true"]}` (IoU=1.000) |
| Campaign_064b76319fb7a73c | `{"Region": ["978039453340"], "Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A"], "Child": ["false", "true"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 3: `{"Region": ["978039453340", "993919383527", "921019383527"], "Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_C"], "Child": ["false", "true"]}` (IoU=0.946) |
| Campaign_45ed2c60a5c996aa | `{"Region": ["952038632934", "967133361069", "975742714340"]}` | № 4: `{"Region": ["952038632934"]}` (IoU=0.994)<br>№ 7: `{"Region": ["975742714340"]}` (IoU=0.003) | № 1: `{"Region": ["952038632934", "975742714340"]}` (IoU=0.997) | № 1: `{"Region": ["952038632934", "975742714340"]}` (IoU=0.997) | № 1: `{"Region": ["952038632934", "975742714340"]}` (IoU=0.997) | № 2: `{"Region": ["952038632934", "967133361069", "975742714340"]}` (IoU=1.000) |
| Campaign_4961bb5390cb999b | `{"Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_C"], "Child": ["true"]}` | № 2: `{"Child": ["true"]}` (IoU=0.901) | № 2: `{"Child": ["true"]}` (IoU=0.901) | № 2: `{"Child": ["true"]}` (IoU=0.901) | № 2: `{"Child": ["true"]}` (IoU=0.901) | № 5: `{"Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Child": ["true"]}` (IoU=0.994) |
| Campaign_3218c1beec1563dc | `{"Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A"], "Child": ["false", "true"], "Category": ["998574152217"]}` | № 3: `{"Category": ["998574152217"]}` (IoU=0.943) | № 3: `{"Category": ["998574152217"]}` (IoU=0.943) | № 3: `{"Category": ["998574152217"]}` (IoU=0.943) | № 5: `{"Category": ["998574152217"]}` (IoU=0.943) | № 7: `{"Category": ["998574152217"]}` (IoU=0.943) |
| Campaign_853541fecb118ddf | `{"Category": ["937708072325", "937461435530"]}` | № 5: `{"Category": ["937708072325"]}` (IoU=0.690)<br>№ 6: `{"Category": ["937461435530"]}` (IoU=0.310) | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Campaign_3f4ead5ce72d78b1 | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Channel": ["<other>", "966362174317", "972814775321"]}` | № 8: `{"Channel": ["966362174317"]}` (IoU=0.004) | № 5: `{"Channel": ["966362174317"]}` (IoU=0.004) | № 5: `{"Channel": ["966362174317"]}` (IoU=0.004) | № 7: `{"Channel": ["<other>"]}` (IoU=0.526)<br>№ 8: `{"Channel": ["966362174317"]}` (IoU=0.004) | № 1: `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Channel": ["<other>", "952080524534", "966362174317", "972814775321"]}` (IoU=0.995) |

## What was inside.

- **Campaign_66064f3dd9c1af0b**: targeting `{"Category": ["937456303809"]}`; impressions train/test=83600/59610; plan=453503; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_e0698aae09dcee95**: targeting `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "Child": ["false", "true"]}`; impressions train/test=18538/12812; plan=91141; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_064b76319fb7a73c**: targeting `{"Region": ["978039453340"], "Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A"], "Child": ["false", "true"]}`; impressions train/test=16806/11916; plan=108222; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_45ed2c60a5c996aa**: targeting `{"Region": ["952038632934", "967133361069", "975742714340"]}`; impressions train/test=16201/14265; plan=77517; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_4961bb5390cb999b**: targeting `{"Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_C"], "Child": ["true"]}`; impressions train/test=65326/50613; plan=310896; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_3218c1beec1563dc**: targeting `{"Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A"], "Child": ["false", "true"], "Category": ["998574152217"]}`; impressions train/test=23939/16955; plan=144688; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_853541fecb118ddf**: targeting `{"Category": ["937708072325", "937461435530"]}`; impressions train/test=7181/5189; plan=95867; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_3f4ead5ce72d78b1**: targeting `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Channel": ["<other>", "966362174317", "972814775321"]}`; impressions train/test=30902/25236; plan=158533; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.

## single_feature predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Category": ["937456303809"]}` | 1.000 | 94931 / 94931 | 0 | Campaign_66064f3dd9c1af0b | 1.000 |
| 2 | `{"Child": ["true"]}` | 0.951 | 70477 / 67053 | 0 | Campaign_4961bb5390cb999b | 0.901 |
| 3 | `{"Category": ["998574152217"]}` | 0.945 | 32050 / 30285 | 0 | Campaign_3218c1beec1563dc | 0.943 |
| 4 | `{"Region": ["952038632934"]}` | 1.000 | 16080 / 16080 | 0 | Campaign_45ed2c60a5c996aa | 0.994 |
| 5 | `{"Category": ["937708072325"]}` | 1.000 | 14150 / 14150 | 0 | Campaign_853541fecb118ddf | 0.690 |
| 6 | `{"Category": ["937461435530"]}` | 1.000 | 5955 / 5955 | 0 | Campaign_853541fecb118ddf | 0.310 |
| 7 | `{"Region": ["975742714340"]}` | 0.991 | 104 / 104 | 0 | Campaign_45ed2c60a5c996aa | 0.003 |
| 8 | `{"Channel": ["966362174317"]}` | 0.696 | 192 / 134 | 0 | Campaign_3f4ead5ce72d78b1 | 0.004 |

## dnf_beam predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["952038632934", "975742714340"]}` | 1.000 | 16184 / 16184 | 0 | Campaign_45ed2c60a5c996aa | 0.997 |
| 2 | `{"Child": ["true"]}` | 0.951 | 70477 / 67053 | 0 | Campaign_4961bb5390cb999b | 0.901 |
| 3 | `{"Category": ["998574152217"]}` | 0.945 | 32050 / 30285 | 0 | Campaign_3218c1beec1563dc | 0.943 |
| 4 | `{"Category": ["937456303809", "937708072325", "937461435530"]}` | 1.000 | 115036 / 115036 | 0 | Campaign_66064f3dd9c1af0b | 0.821 |
| 5 | `{"Channel": ["966362174317"]}` | 0.696 | 192 / 134 | 0 | Campaign_3f4ead5ce72d78b1 | 0.004 |

## dnf_cooldown_fsm predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["952038632934", "975742714340"]}` | 1.000 | 16184 / 16184 | 0 | Campaign_45ed2c60a5c996aa | 0.997 |
| 2 | `{"Child": ["true"]}` | 0.951 | 70477 / 67053 | 0 | Campaign_4961bb5390cb999b | 0.901 |
| 3 | `{"Category": ["998574152217"]}` | 0.945 | 32050 / 30285 | 0 | Campaign_3218c1beec1563dc | 0.943 |
| 4 | `{"Category": ["937456303809", "937708072325", "937461435530"]}` | 1.000 | 115036 / 115036 | 0 | Campaign_66064f3dd9c1af0b | 0.821 |
| 5 | `{"Channel": ["966362174317"]}` | 0.696 | 192 / 134 | 0 | Campaign_3f4ead5ce72d78b1 | 0.004 |

## dnf_validated predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["952038632934", "975742714340"]}` | 1.000 | 16184 / 16184 | 0 | Campaign_45ed2c60a5c996aa | 0.997 |
| 2 | `{"Child": ["true"]}` | 0.951 | 70477 / 67053 | 0 | Campaign_4961bb5390cb999b | 0.901 |
| 3 | `{"Region": ["939929993546"], "Child": ["false"]}` | 0.995 | 184 / 184 | 0 | Campaign_e0698aae09dcee95 | 0.000 |
| 4 | `{"Device": ["SMART_TV_PLATFORM_C"], "Child": ["false"]}` | 1.000 | 15790 / 15790 | 0 | Campaign_e0698aae09dcee95 | 0.828 |
| 5 | `{"Category": ["998574152217"]}` | 0.945 | 32050 / 30285 | 0 | Campaign_3218c1beec1563dc | 0.943 |
| 6 | `{"Category": ["937456303809", "937708072325", "937461435530"]}` | 1.000 | 115036 / 115036 | 0 | Campaign_66064f3dd9c1af0b | 0.821 |
| 7 | `{"Channel": ["<other>"]}` | 0.550 | 62877 / 34609 | 0 | Campaign_3f4ead5ce72d78b1 | 0.526 |
| 8 | `{"Channel": ["966362174317"]}` | 0.696 | 192 / 134 | 0 | Campaign_3f4ead5ce72d78b1 | 0.004 |

## motif_noisy_or predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Channel": ["<other>", "952080524534", "966362174317", "972814775321"]}` | 0.999 | 33440 / 33420 | 0 | Campaign_3f4ead5ce72d78b1 | 0.995 |
| 2 | `{"Region": ["952038632934", "967133361069", "975742714340"]}` | 1.000 | 16207 / 16207 | 0 | Campaign_45ed2c60a5c996aa | 1.000 |
| 3 | `{"Region": ["978039453340", "993919383527", "921019383527"], "Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_C"], "Child": ["false", "true"]}` | 1.000 | 23879 / 23879 | 0 | Campaign_064b76319fb7a73c | 0.946 |
| 4 | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"], "Child": ["false", "true"]}` | 1.000 | 19163 / 19163 | 0 | Campaign_e0698aae09dcee95 | 1.000 |
| 5 | `{"Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Child": ["true"]}` | 1.000 | 65155 / 65155 | 0 | Campaign_4961bb5390cb999b | 0.994 |
| 6 | `{"Category": ["937456303809", "937708072325", "937461435530"]}` | 1.000 | 115036 / 115036 | 0 | Campaign_66064f3dd9c1af0b | 0.821 |
| 7 | `{"Category": ["998574152217"]}` | 0.931 | 32050 / 30285 | 0 | Campaign_3218c1beec1563dc | 0.943 |
