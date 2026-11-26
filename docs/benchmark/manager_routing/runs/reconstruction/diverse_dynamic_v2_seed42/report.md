# Rebuilding Hidden Campaigns

Input algorithms: query features, time, user, 200/204. Winners and seller configuration are used only in the evaluation.

Train: 89,464; test: 29,998. Time breakdown; auction is not reset at the border.

IoU targeting is weighted by profile frequencies **only sent test queries**. Campaign matching: greedy mutually unambiguous at IoU ≥ 0.5.Recall includes campaigns without impressions; outside of test traffic, targeting is not checked.

Campaigns with the same observed behavior are unidentifiable. Rules found are hypotheses: names, CPM, budget, exact frequencies, and flutes are not restored. Cooldown is the total heuristic range of hypotheses, not the min_interval measured real-world campaign.

motif_noisy_or: P(200)=1−(1−background)∏(1−activation) coincidentally. In his table P(200) indicates the probability of activation of a particular motif, Not the full probability of a response when crossing the rules.

## Comparison of algorithms

| Algorithm | Hypotheses | Brier ↓ | Logloss ↓ | Accuracy | Precision campaign | Recall campaign | IoU union |
|---|---:|---:|---:|---:|---:|---:|---:|
| single_feature | 0 | 0.1314 | 0.4327 | 0.845 | 0.000 | 0.000 | 0.000 |
| dnf_beam | 0 | 0.1314 | 0.4327 | 0.845 | 0.000 | 0.000 | 0.000 |
| dnf_cooldown_fsm | 0 | 0.1314 | 0.4327 | 0.845 | 0.000 | 0.000 | 0.000 |
| dnf_validated | 8 | 0.1126 | 0.3736 | 0.845 | 0.375 | 0.375 | 0.409 |
| motif_noisy_or | 11 | 0.0915 | 0.2861 | 0.871 | 0.455 | 0.625 | 0.911 |

The constant (share of 200 in train): Brier=0.1314, Logloss=0.4327.

Static models don't use test responses. FSM first produces a prediction, then receives the actual 200/204 for the next query. FSM parameters are selected on the inner tail of the train; the initial test state is heated by the train history.

## Real and Restored Targeting

Each line has a real campaign, next to each algorithm's closest hypothesis with numbers from the prediction sections and the IoU. Each hypothesis is shown at its nearest real campaign, including IoU < 0.5; this does not mean that the campaign is restored. "No immediate hypotheses" means that no hypothesis has chosen this campaign as the nearest one. Empty targeting is shown as "No Limits."

| A real campaign | Real-life targeting | single_feature | dnf_beam | dnf_cooldown_fsm | dnf_validated | motif_noisy_or |
|---|---|---|---|---|---|---|
| Campaign_66064f3dd9c1af0b | `{"Category": ["937456303809"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 5: `{"Category": ["937456303809"]}` (IoU=1.000) | № 2: `{"Region": ["915202053340", "946620753340", "915202367527", "946621486443", "915203729004", "915203100630", "915203519546", "915203624275", "902319069340", "974905091798", "902423798340", "903575817340", "902947443340", "903261630340", "902109611340", "902528527340", "902842714340", "902005301256", "903366464069", "903471088340", "902215911275", "902842819069", "902005196527", "902215806546"], "Category": ["937456303809"]}` (IoU=0.360)<br>№ 4: `{"Category": ["937456303809", "937473688823", "998574152217"]}` (IoU=0.568) |
| Campaign_e0698aae09dcee95 | `{"Child": ["false", "true"], "Category": ["937473688823", "998574152217"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Campaign_064b76319fb7a73c | `{"Device": ["SET_TOP_BOX_A", "STREAMING_TV_BOX_A"], "Child": ["false"], "Category": ["937473479365"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 9: `{"Category": ["937473479365"]}` (IoU=0.778) |
| Campaign_45ed2c60a5c996aa | `{"Region": ["915202995901", "966923903069"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 1: `{"Region": ["966923903069"]}` (IoU=0.017)<br>№ 7: `{"Channel": ["909716008761"]}` (IoU=0.018) | № 5: `{"Region": ["915203729004", "915202995901", "915203519546", "919962195848", "994023798340", "966923903069"]}` (IoU=0.456) |
| Campaign_4961bb5390cb999b | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Channel": ["<other>", "909716008761"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 8: `{"Device": ["ANDROID_SET_TOP_BOX_A"], "Channel": ["<other>"]}` (IoU=0.854) | № 7: `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Channel": ["<other>", "965158348951", "924619333696", "983715535304", "945605908952"]}` (IoU=0.749) |
| Campaign_3218c1beec1563dc | `{"Region": ["915202053340"], "Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Child": ["false", "true"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 4: `{"Region": ["915202053340", "994023798340"], "Child": ["false"]}` (IoU=0.696) | № 1: `{"Device": ["SMART_TV_PLATFORM_B"], "Category": ["937473688823"]}` (IoU=0.322)<br>№ 6: `{"Region": ["915202053340", "967552172340"], "Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"]}` (IoU=0.561)<br>№ 10: `{"Region": ["915202053340"], "Device": ["SMART_TV_PLATFORM_A"], "Category": ["937456303809"]}` (IoU=0.297) |
| Campaign_853541fecb118ddf | `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 3: `{"Region": ["936147958069", "952038004560"], "Device": ["ANDROID_SET_TOP_BOX_A"]}` (IoU=0.012)<br>№ 6: `{"Channel": ["924619333696", "983715535304", "945605908952"]}` (IoU=0.028) | № 3: `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"]}` (IoU=0.767)<br>№ 11: `{"Device": ["ANDROID_SET_TOP_BOX_A"], "Channel": ["952037271457", "952026274912", "965153321959", "952074240794", "952037795102", "952074659710", "965158872596", "969933048866", "959854034559", "924936085466", "933321595575", "992032242861"]}` (IoU=0.130) |
| Campaign_3f4ead5ce72d78b1 | `{"Region": ["915203729004", "915203519546", "921019383527"], "Device": ["SET_TOP_BOX_A", "ANDROID_TV_A", "SMART_TV_PLATFORM_B"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 2: `{"Region": ["915203729004"], "Device": ["ANDROID_TV_A"]}` (IoU=0.038) | № 8: `{"Region": ["915203729004", "915203519546", "921019383527"], "Device": ["ANDROID_TV_A", "SMART_TV_PLATFORM_B"]}` (IoU=0.134) |

## What was inside.

- **Campaign_66064f3dd9c1af0b**: targeting `{"Category": ["937456303809"]}`; impressions train/test=3060/965; plan=36382; min_interval=0; user limits=((4, 86400),); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_e0698aae09dcee95**: targeting `{"Child": ["false", "true"], "Category": ["937473688823", "998574152217"]}`; impressions train/test=1843/797; plan=24367; min_interval=30; user limits=((8, 86400),); ad limits=((889, 3600), (10966, 86400)); flight=0…1152921504606846976 s.
- **Campaign_064b76319fb7a73c**: targeting `{"Device": ["SET_TOP_BOX_A", "STREAMING_TV_BOX_A"], "Child": ["false"], "Category": ["937473479365"]}`; impressions train/test=759/283; plan=14437; min_interval=120; user limits=((16, 86400),); ad limits=((76, 600), (301, 3600), (4693, 86400)); flight=0…1152921504606846976 s.
- **Campaign_45ed2c60a5c996aa**: targeting `{"Region": ["915202995901", "966923903069"]}`; impressions train/test=283/87; plan=6684; min_interval=300; user limits=((4, 86400),); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_4961bb5390cb999b**: targeting `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Channel": ["<other>", "909716008761"]}`; impressions train/test=1804/673; plan=10402; min_interval=0; user limits=((8, 86400),); ad limits=((380, 3600), (4681, 86400)); flight=0…1152921504606846976 s.
- **Campaign_3218c1beec1563dc**: targeting `{"Region": ["915202053340"], "Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Child": ["false", "true"]}`; impressions train/test=2165/909; plan=14900; min_interval=30; user limits=((16, 86400),); ad limits=((78, 600), (311, 3600), (4843, 86400)); flight=0…1152921504606846976 s.
- **Campaign_853541fecb118ddf**: targeting `{"Device": ["ANDROID_SET_TOP_BOX_A"]}`; impressions train/test=2399/800; plan=40767; min_interval=120; user limits=((4, 86400),); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_3f4ead5ce72d78b1**: targeting `{"Region": ["915203729004", "915203519546", "921019383527"], "Device": ["SET_TOP_BOX_A", "ANDROID_TV_A", "SMART_TV_PLATFORM_B"]}`; impressions train/test=442/149; plan=7517; min_interval=300; user limits=((8, 86400),); ad limits=((275, 3600), (3383, 86400)); flight=0…1152921504606846976 s.

## single_feature predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| — | There are no rules with sufficient support | | | | | |

## dnf_beam predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| — | There are no rules with sufficient support | | | | | |

## dnf_cooldown_fsm predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| — | There are no rules with sufficient support | | | | | |

## dnf_validated predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["966923903069"]}` | 0.394 | 31 / 12 | 0 | Campaign_45ed2c60a5c996aa | 0.017 |
| 2 | `{"Region": ["915203729004"], "Device": ["ANDROID_TV_A"]}` | 0.584 | 176 / 103 | 0 | Campaign_3f4ead5ce72d78b1 | 0.038 |
| 3 | `{"Region": ["936147958069", "952038004560"], "Device": ["ANDROID_SET_TOP_BOX_A"]}` | 0.497 | 163 / 81 | 0 | Campaign_853541fecb118ddf | 0.012 |
| 4 | `{"Region": ["915202053340", "994023798340"], "Child": ["false"]}` | 0.433 | 7077 / 3061 | 0 | Campaign_3218c1beec1563dc | 0.696 |
| 5 | `{"Category": ["937456303809"]}` | 0.306 | 13717 / 4201 | 0 | Campaign_66064f3dd9c1af0b | 1.000 |
| 6 | `{"Channel": ["924619333696", "983715535304", "945605908952"]}` | 0.246 | 907 / 223 | 0 | Campaign_853541fecb118ddf | 0.028 |
| 7 | `{"Channel": ["909716008761"]}` | 0.346 | 50 / 17 | 0 | Campaign_45ed2c60a5c996aa | 0.018 |
| 8 | `{"Device": ["ANDROID_SET_TOP_BOX_A"], "Channel": ["<other>"]}` | 0.416 | 3417 / 1422 | 0 | Campaign_4961bb5390cb999b | 0.854 |

## motif_noisy_or predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Device": ["SMART_TV_PLATFORM_B"], "Category": ["937473688823"]}` | 0.842 | 1388 / 1211 | 0 | Campaign_3218c1beec1563dc | 0.322 |
| 2 | `{"Region": ["915202053340", "946620753340", "915202367527", "946621486443", "915203729004", "915203100630", "915203519546", "915203624275", "902319069340", "974905091798", "902423798340", "903575817340", "902947443340", "903261630340", "902109611340", "902528527340", "902842714340", "902005301256", "903366464069", "903471088340", "902215911275", "902842819069", "902005196527", "902215806546"], "Category": ["937456303809"]}` | 0.233 | 4245 / 2245 | 0 | Campaign_66064f3dd9c1af0b | 0.360 |
| 3 | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"]}` | 0.094 | 19983 / 5372 | 0 | Campaign_853541fecb118ddf | 0.767 |
| 4 | `{"Category": ["937456303809", "937473688823", "998574152217"]}` | 0.193 | 22917 / 6988 | 0 | Campaign_66064f3dd9c1af0b | 0.568 |
| 5 | `{"Region": ["915203729004", "915202995901", "915203519546", "919962195848", "994023798340", "966923903069"]}` | 0.113 | 5578 / 1318 | 0 | Campaign_45ed2c60a5c996aa | 0.456 |
| 6 | `{"Region": ["915202053340", "967552172340"], "Device": ["SET_TOP_BOX_A", "ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"]}` | 0.130 | 5327 / 2093 | 0 | Campaign_3218c1beec1563dc | 0.561 |
| 7 | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Channel": ["<other>", "965158348951", "924619333696", "983715535304", "945605908952"]}` | 0.392 | 5475 / 2489 | 0 | Campaign_4961bb5390cb999b | 0.749 |
| 8 | `{"Region": ["915203729004", "915203519546", "921019383527"], "Device": ["ANDROID_TV_A", "SMART_TV_PLATFORM_B"]}` | 0.520 | 335 / 195 | 0 | Campaign_3f4ead5ce72d78b1 | 0.134 |
| 9 | `{"Category": ["937473479365"]}` | 0.099 | 7654 / 917 | 0 | Campaign_064b76319fb7a73c | 0.778 |
| 10 | `{"Region": ["915202053340"], "Device": ["SMART_TV_PLATFORM_A"], "Category": ["937456303809"]}` | 0.531 | 1354 / 1044 | 0 | Campaign_3218c1beec1563dc | 0.297 |
| 11 | `{"Device": ["ANDROID_SET_TOP_BOX_A"], "Channel": ["952037271457", "952026274912", "965153321959", "952074240794", "952037795102", "952074659710", "965158872596", "969933048866", "959854034559", "924936085466", "933321595575", "992032242861"]}` | 0.246 | 2084 / 668 | 0 | Campaign_853541fecb118ddf | 0.130 |
