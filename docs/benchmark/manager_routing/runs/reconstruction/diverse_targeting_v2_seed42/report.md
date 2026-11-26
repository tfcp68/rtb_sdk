# Rebuilding Hidden Campaigns

Input algorithms: query features, time, user, 200/204. Winners and seller configuration are used only in the evaluation.

Train: 89,464; test: 29,998. Time breakdown; auction is not reset at the border.

IoU targeting is weighted by profile frequencies **only sent test queries**. Campaign matching: greedy mutually unambiguous at IoU ≥ 0.5.Recall includes campaigns without impressions; outside of test traffic, targeting is not checked.

Campaigns with the same observed behavior are unidentifiable. Rules found are hypotheses: names, CPM, budget, exact frequencies, and flutes are not restored. Cooldown is the total heuristic range of hypotheses, not the min_interval measured real-world campaign.

motif_noisy_or: P(200)=1−(1−background)∏(1−activation) coincidentally. In his table P(200) indicates the probability of activation of a particular motif, Not the full probability of a response when crossing the rules.

## Comparison of algorithms

| Algorithm | Hypotheses | Brier ↓ | Logloss ↓ | Accuracy | Precision campaign | Recall campaign | IoU union |
|---|---:|---:|---:|---:|---:|---:|---:|
| single_feature | 10 | 0.0320 | 0.1216 | 0.963 | 0.500 | 0.625 | 0.933 |
| dnf_beam | 4 | 0.0320 | 0.1216 | 0.963 | 0.750 | 0.375 | 0.933 |
| dnf_cooldown_fsm | 4 | 0.0320 | 0.1216 | 0.963 | 0.750 | 0.375 | 0.933 |
| dnf_validated | 4 | 0.0320 | 0.1216 | 0.963 | 0.750 | 0.375 | 0.933 |
| motif_noisy_or | 9 | 0.0010 | 0.0045 | 0.999 | 0.333 | 0.375 | 0.984 |

The constant (share of 200 in train): Brier=0.2488, Logloss=0.6908.

Static models don't use test responses. FSM first produces a prediction, then receives the actual 200/204 for the next query. FSM parameters are selected on the inner tail of the train; the initial test state is heated by the train history.

## Real and Restored Targeting

Each line has a real campaign, next to each algorithm's closest hypothesis with numbers from the prediction sections and the IoU. Each hypothesis is shown at its nearest real campaign, including IoU < 0.5; this does not mean that the campaign is restored. "No immediate hypotheses" means that no hypothesis has chosen this campaign as the nearest one. Empty targeting is shown as "No Limits."

| A real campaign | Real-life targeting | single_feature | dnf_beam | dnf_cooldown_fsm | dnf_validated | motif_noisy_or |
|---|---|---|---|---|---|---|
| Campaign_66064f3dd9c1af0b | `{"Category": ["937456303809"]}` | № 2: `{"Category": ["937456303809"]}` (IoU=1.000) | № 4: `{"Category": ["937456303809", "937473688823", "998574152217"]}` (IoU=0.568) | № 4: `{"Category": ["937456303809", "937473688823", "998574152217"]}` (IoU=0.568) | № 4: `{"Category": ["937456303809", "937473688823", "998574152217"]}` (IoU=0.568) | № 2: `{"Category": ["937456303809", "937473688823", "998574152217"]}` (IoU=0.568) |
| Campaign_e0698aae09dcee95 | `{"Child": ["false", "true"], "Category": ["937473688823", "998574152217"]}` | № 3: `{"Category": ["998574152217"]}` (IoU=0.445)<br>№ 4: `{"Category": ["937473688823"]}` (IoU=0.555) | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |
| Campaign_064b76319fb7a73c | `{"Device": ["SET_TOP_BOX_A", "STREAMING_TV_BOX_A"], "Child": ["false"], "Category": ["937473479365"]}` | № 5: `{"Category": ["937473479365"]}` (IoU=0.778) | № 3: `{"Category": ["937473479365"]}` (IoU=0.778) | № 3: `{"Category": ["937473479365"]}` (IoU=0.778) | № 3: `{"Category": ["937473479365"]}` (IoU=0.778) | № 3: `{"Device": ["SET_TOP_BOX_A"], "Child": ["false"], "Category": ["937473479365"]}` (IoU=1.000) |
| Campaign_45ed2c60a5c996aa | `{"Region": ["915202995901", "966923903069"]}` | № 6: `{"Region": ["915202995901"]}` (IoU=0.983)<br>№ 9: `{"Region": ["966923903069"]}` (IoU=0.017) | № 1: `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` (IoU=0.496) | № 1: `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` (IoU=0.496) | № 1: `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` (IoU=0.496) | № 4: `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` (IoU=0.496) |
| Campaign_4961bb5390cb999b | `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Channel": ["<other>", "909716008761"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 6: `{"Device": ["SMART_TV_PLATFORM_A"], "Channel": ["<other>", "909716008761"]}` (IoU=0.133) |
| Campaign_3218c1beec1563dc | `{"Region": ["915202053340"], "Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Child": ["false", "true"]}` | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | № 5: `{"Region": ["915202053340"], "Device": ["SET_TOP_BOX_A"]}` (IoU=0.339)<br>№ 7: `{"Region": ["915202053340"], "Category": ["909258896386", "935221236911", "937474003010", "937461435530", "937707653409", "937473898281", "916432770036", "937459026763", "991347707320", "985261734840", "949119452980"]}` (IoU=0.148)<br>№ 8: `{"Region": ["915202053340"], "Child": ["true"]}` (IoU=0.126)<br>№ 9: `{"Region": ["915202053340"], "Category": ["961393278034", "909257115993", "961390240893", "937458922034", "926770037898"]}` (IoU=0.017) |
| Campaign_853541fecb118ddf | `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` | № 1: `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` (IoU=1.000) | № 2: `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` (IoU=1.000) | № 2: `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` (IoU=1.000) | № 2: `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` (IoU=1.000) | № 1: `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` (IoU=1.000) |
| Campaign_3f4ead5ce72d78b1 | `{"Region": ["915203729004", "915203519546", "921019383527"], "Device": ["SET_TOP_BOX_A", "ANDROID_TV_A", "SMART_TV_PLATFORM_B"]}` | № 7: `{"Region": ["915203729004"]}` (IoU=0.348)<br>№ 8: `{"Region": ["915203519546"]}` (IoU=0.483)<br>№ 10: `{"Region": ["921019383527"]}` (IoU=0.119) | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses | No nearby hypotheses |

## What was inside.

- **Campaign_66064f3dd9c1af0b**: targeting `{"Category": ["937456303809"]}`; impressions train/test=10073/3106; plan=36382; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_e0698aae09dcee95**: targeting `{"Child": ["false", "true"], "Category": ["937473688823", "998574152217"]}`; impressions train/test=8773/2981; plan=24367; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_064b76319fb7a73c**: targeting `{"Device": ["SET_TOP_BOX_A", "STREAMING_TV_BOX_A"], "Child": ["false"], "Category": ["937473479365"]}`; impressions train/test=4825/1734; plan=14437; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_45ed2c60a5c996aa**: targeting `{"Region": ["915202995901", "966923903069"]}`; impressions train/test=1900/690; plan=6684; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_4961bb5390cb999b**: targeting `{"Device": ["ANDROID_SET_TOP_BOX_A", "SMART_TV_PLATFORM_A"], "Channel": ["<other>", "909716008761"]}`; impressions train/test=3947/1593; plan=10402; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_3218c1beec1563dc**: targeting `{"Region": ["915202053340"], "Device": ["SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"], "Child": ["false", "true"]}`; impressions train/test=3687/1174; plan=14900; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_853541fecb118ddf**: targeting `{"Device": ["ANDROID_SET_TOP_BOX_A"]}`; impressions train/test=11390/3945; plan=40767; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.
- **Campaign_3f4ead5ce72d78b1**: targeting `{"Region": ["915203729004", "915203519546", "921019383527"], "Device": ["SET_TOP_BOX_A", "ANDROID_TV_A", "SMART_TV_PLATFORM_B"]}`; impressions train/test=2852/813; plan=7517; min_interval=0; user limits=(); ad limits=(); flight=0…1152921504606846976 s.

## single_feature predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` | 1.000 | 15336 / 15336 | 0 | Campaign_853541fecb118ddf | 1.000 |
| 2 | `{"Category": ["937456303809"]}` | 1.000 | 13717 / 13717 | 0 | Campaign_66064f3dd9c1af0b | 1.000 |
| 3 | `{"Category": ["998574152217"]}` | 1.000 | 4816 / 4816 | 0 | Campaign_e0698aae09dcee95 | 0.445 |
| 4 | `{"Category": ["937473688823"]}` | 1.000 | 4384 / 4384 | 0 | Campaign_e0698aae09dcee95 | 0.555 |
| 5 | `{"Category": ["937473479365"]}` | 0.757 | 7654 / 5796 | 0 | Campaign_064b76319fb7a73c | 0.778 |
| 6 | `{"Region": ["915202995901"]}` | 1.000 | 2490 / 2490 | 0 | Campaign_45ed2c60a5c996aa | 0.983 |
| 7 | `{"Region": ["915203729004"]}` | 0.993 | 1302 / 1294 | 0 | Campaign_3f4ead5ce72d78b1 | 0.348 |
| 8 | `{"Region": ["915203519546"]}` | 0.996 | 1372 / 1367 | 0 | Campaign_3f4ead5ce72d78b1 | 0.483 |
| 9 | `{"Region": ["966923903069"]}` | 0.970 | 31 / 31 | 0 | Campaign_45ed2c60a5c996aa | 0.017 |
| 10 | `{"Region": ["921019383527"]}` | 0.988 | 419 / 415 | 0 | Campaign_3f4ead5ce72d78b1 | 0.119 |

## dnf_beam predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` | 0.997 | 5614 / 5597 | 0 | Campaign_45ed2c60a5c996aa | 0.496 |
| 2 | `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` | 1.000 | 15336 / 15336 | 0 | Campaign_853541fecb118ddf | 1.000 |
| 3 | `{"Category": ["937473479365"]}` | 0.757 | 7654 / 5796 | 0 | Campaign_064b76319fb7a73c | 0.778 |
| 4 | `{"Category": ["937456303809", "937473688823", "998574152217"]}` | 1.000 | 22917 / 22917 | 0 | Campaign_66064f3dd9c1af0b | 0.568 |

## dnf_cooldown_fsm predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` | 0.997 | 5614 / 5597 | 0 | Campaign_45ed2c60a5c996aa | 0.496 |
| 2 | `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` | 1.000 | 15336 / 15336 | 0 | Campaign_853541fecb118ddf | 1.000 |
| 3 | `{"Category": ["937473479365"]}` | 0.757 | 7654 / 5796 | 0 | Campaign_064b76319fb7a73c | 0.778 |
| 4 | `{"Category": ["937456303809", "937473688823", "998574152217"]}` | 1.000 | 22917 / 22917 | 0 | Campaign_66064f3dd9c1af0b | 0.568 |

## dnf_validated predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` | 0.997 | 5614 / 5597 | 0 | Campaign_45ed2c60a5c996aa | 0.496 |
| 2 | `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` | 1.000 | 15336 / 15336 | 0 | Campaign_853541fecb118ddf | 1.000 |
| 3 | `{"Category": ["937473479365"]}` | 0.757 | 7654 / 5796 | 0 | Campaign_064b76319fb7a73c | 0.778 |
| 4 | `{"Category": ["937456303809", "937473688823", "998574152217"]}` | 1.000 | 22917 / 22917 | 0 | Campaign_66064f3dd9c1af0b | 0.568 |

## motif_noisy_or predictions

| № | Targeting hypothesis | P(200) | Observations / 200 | Cooldown, s | The nearest real | IoU |
|---|---|---:|---:|---:|---|---:|
| 1 | `{"Device": ["ANDROID_SET_TOP_BOX_A"]}` | 1.000 | 15336 / 15336 | 0 | Campaign_853541fecb118ddf | 1.000 |
| 2 | `{"Category": ["937456303809", "937473688823", "998574152217"]}` | 1.000 | 22917 / 22917 | 0 | Campaign_66064f3dd9c1af0b | 0.568 |
| 3 | `{"Device": ["SET_TOP_BOX_A"], "Child": ["false"], "Category": ["937473479365"]}` | 1.000 | 5526 / 5526 | 0 | Campaign_064b76319fb7a73c | 1.000 |
| 4 | `{"Region": ["915203729004", "915202995901", "915203519546", "921019383527", "966923903069"]}` | 0.992 | 5614 / 5597 | 0 | Campaign_45ed2c60a5c996aa | 0.496 |
| 5 | `{"Region": ["915202053340"], "Device": ["SET_TOP_BOX_A"]}` | 0.013 | 3254 / 2668 | 0 | Campaign_3218c1beec1563dc | 0.339 |
| 6 | `{"Device": ["SMART_TV_PLATFORM_A"], "Channel": ["<other>", "909716008761"]}` | 1.000 | 513 / 513 | 0 | Campaign_4961bb5390cb999b | 0.133 |
| 7 | `{"Region": ["915202053340"], "Category": ["909258896386", "935221236911", "937474003010", "937461435530", "937707653409", "937473898281", "916432770036", "937459026763", "991347707320", "985261734840", "949119452980"]}` | 0.972 | 965 / 952 | 0 | Campaign_3218c1beec1563dc | 0.148 |
| 8 | `{"Region": ["915202053340"], "Child": ["true"]}` | 0.859 | 775 / 765 | 0 | Campaign_3218c1beec1563dc | 0.126 |
| 9 | `{"Region": ["915202053340"], "Category": ["961393278034", "909257115993", "961390240893", "937458922034", "926770037898"]}` | 0.781 | 166 / 141 | 0 | Campaign_3218c1beec1563dc | 0.017 |
