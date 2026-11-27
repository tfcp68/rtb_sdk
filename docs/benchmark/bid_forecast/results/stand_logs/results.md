# Results on stand logs

Closed-stand generated response logs; no valid market-price benchmark labels

Generator: `benchmarks/closed_stand/stand.py::simulate + Seller`; sample=0.000296; seeds=[19, 43, 71].
The stand's price of 200 is an internal fixed payout. It is not a clearing price and is never used as a market-price label.

## Generated periods

| seed | phase | days | processed | sent | 200 | sell-through | seconds |
|---:|---|---|---:|---:|---:|---:|---:|
| 19 | training | 0:3 | 30804 | 12802 | 6845 | 0.5347 | 0.93 |
| 19 | validation | 3:5 | 16918 | 8209 | 4844 | 0.5901 | 0.47 |
| 19 | test | 5:7 | 19432 | 9807 | 5515 | 0.5624 | 0.65 |
| 43 | training | 0:3 | 30804 | 12844 | 6873 | 0.5351 | 1.31 |
| 43 | validation | 3:5 | 16918 | 8242 | 4871 | 0.5910 | 0.76 |
| 43 | test | 5:7 | 19432 | 9858 | 5511 | 0.5590 | 0.54 |
| 71 | training | 0:3 | 30804 | 12746 | 6815 | 0.5347 | 0.94 |
| 71 | validation | 3:5 | 16918 | 8209 | 4811 | 0.5861 | 0.49 |
| 71 | test | 5:7 | 19432 | 9828 | 5486 | 0.5582 | 0.59 |

## Models and scores

| seed | paper / scope | variant | train | test | Brier | log-loss | fit (s) | predict (s) |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 19 | stand_response_baseline | TRAIN_CONSTANT | 12802 | 9807 | 0.24687775394936165 | 0.6868945811329484 | 0.0 | 0.0 |
| 19 | stand_response_baseline | VALIDATION_SELECTED_CONSTANT | 12802 | 9807 | 0.24688103889635343 | 0.6869305656659136 | 0.0 | 0.0 |
| 19 | Cui2011 | not_evaluable_on_stand_schema |  |  |  |  |  |  |
| 19 | Wang2016 | not_evaluable_on_stand_schema |  |  |  |  |  |  |
| 43 | stand_response_baseline | TRAIN_CONSTANT | 12844 | 9858 | 0.24708686384531073 | 0.6873133366315042 | 0.0 | 0.0 |
| 43 | stand_response_baseline | VALIDATION_SELECTED_CONSTANT | 12844 | 9858 | 0.24753585068200057 | 0.6882572738656607 | 0.0 | 0.0 |
| 43 | Cui2011 | not_evaluable_on_stand_schema |  |  |  |  |  |  |
| 43 | Wang2016 | not_evaluable_on_stand_schema |  |  |  |  |  |  |
| 71 | stand_response_baseline | TRAIN_CONSTANT | 12746 | 9828 | 0.2471659924554079 | 0.6874719867508773 | 0.0 | 0.0 |
| 71 | stand_response_baseline | VALIDATION_SELECTED_CONSTANT | 12746 | 9828 | 0.24738898458592865 | 0.6879475683500962 | 0.0 | 0.0 |
| 71 | Cui2011 | not_evaluable_on_stand_schema |  |  |  |  |  |  |
| 71 | Wang2016 | not_evaluable_on_stand_schema |  |  |  |  |  |  |

## Interpretation limits

- closed stand outputs manager's simulated 200/204 response only; no independent market-price labels.
- Wang exact-price ANLP/CDF cannot be validly computed: no market price or censored submitted-bid threshold exists.
- Cui winning-bid/campaign bid landscape also cannot be evaluated on this schema.
- Wang MM cannot be evaluated here; the Wang source only gives a brief description and external Wu et al. (2015) method, not a sufficient implementation specification.
