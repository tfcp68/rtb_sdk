# auction / examples

Basic Auction call examples: preparing two ad campaigns and impression statistics, and running different ad selection strategies.

Run from the repository root as modules so that the project's root packages are imported without manually changing `sys.path`.

---

## Commands

```powershell
python -m examples.auction.best_one
python -m examples.auction.random_one
python -m examples.auction.best_price
python -m examples.auction.random_price
python -m examples.auction.best_velocity
python -m examples.auction.random_velocity
python -m examples.auction.best_heuristics
python -m examples.auction.random_heuristics

python -m pytest tests/auction
```

## fixtures

`fixtures.py` prepares a common set of input data for all examples:

| Name | Description |
|---|---|
| `test_ad1` | Ad campaign with CPM `1000`, priority `1`, and volume `1000` |
| `test_ad2` | Ad campaign with CPM `500`, priority `1`, and volume `200` |
| `test_ads1` | `AdsDict` with two ads |
| `test_stats1` | `AdStats` with granulated statistics for the two ads |

## best_one / random_one

Show strategies that ignore price and statistics:

| File | Strategy |
|---|---|
| `best_one.py` | `SelectionFunc.BEST_ONE` |
| `random_one.py` | `SelectionFunc.RANDOM_ONE` |

The scripts create `AuctionParams`, call `auction(ads=test_ads1, parameters=params)`, and print the selected ad.

## best_price / random_price

Show price-based selection strategies:

| File | Strategy |
|---|---|
| `best_price.py` | `SelectionFunc.BEST_PRICE` |
| `random_price.py` | `SelectionFunc.RANDOM_PRICE` |

`BEST_PRICE` selects the ad with the highest price; `RANDOM_PRICE` selects randomly, weighted by price.

## best_velocity / random_velocity

Show strategies that select by delivery velocity relative to the plan:

| File | Strategy |
|---|---|
| `best_velocity.py` | `SelectionFunc.BEST_VELOCITY` |
| `random_velocity.py` | `SelectionFunc.RANDOM_VELOCITY` |

Both strategies use `test_stats1`, because the calculation depends on accumulated impression statistics.

## best_heuristics / random_heuristics

Show heuristic strategies that combine price, priority, velocity, and rarity:

| File | Strategy |
|---|---|
| `best_heuristics.py` | `SelectionFunc.BEST_HEURISTICS` |
| `random_heuristics.py` | `SelectionFunc.RANDOM_HEURISTICS` |

Both strategies use `test_stats1`. `BEST_HEURISTICS` selects the best option; `RANDOM_HEURISTICS` selects randomly with heuristic weights.

## Input data

The examples do not read external files. All input data comes from `examples/auction/fixtures.py`.

## Output data

The scripts do not save anything to disk. The result is printed to stdout:

| Output | Description |
|---|---|
| `ad` | The selected ad (`Ad`), or `None` if there is no suitable ad |

## Related tests

Auction tests are located in `tests/auction/`.

| Path | Responsibility |
|---|---|
| `test_auction.py` | Runs parameterized auction cases |
| `cases/` | JSON cases for auction functions |
| `fixtures/` | Test ads, ad dictionaries, and statistics |
| `reports/` | Generated test reports |
