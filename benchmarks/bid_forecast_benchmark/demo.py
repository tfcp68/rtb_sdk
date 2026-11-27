"""Deterministic end-to-end showcase for the two independent paper methods."""

from articles_prorotypes.cui.cui2011 import SegmentForecast, campaign_cdf
from articles_prorotypes.wang.wang2016 import AuctionObservation, SurvivalTree


def main() -> None:
    # Segment moments would normally be forecasts conditioned on targeting samples.
    segment_forecasts = [
        SegmentForecast(mean=1.2, std=0.45, weight=120),
        SegmentForecast(mean=2.4, std=0.8, weight=80),
    ]
    bids = [0.5, 1.0, 2.0, 3.0, 5.0]
    print("Cui 2011: campaign P(market price <= bid)")
    for bid, probability in zip(bids, campaign_cdf(segment_forecasts, bids)):
        print(f"  bid={bid:>4.1f}: {probability:.3f}")

    # The loss rows convey only z > bid; the tree estimates each leaf separately.
    logs = [
        AuctionObservation({"region": "north"}, 1.0, True, market_price=0.7),
        AuctionObservation({"region": "north"}, 2.0, False),
        AuctionObservation({"region": "north"}, 3.0, True, market_price=2.4),
        AuctionObservation({"region": "south"}, 3.0, False),
        AuctionObservation({"region": "south"}, 4.0, True, market_price=3.5),
        AuctionObservation({"region": "south"}, 5.0, True, market_price=4.8),
    ]
    tree = SurvivalTree(max_depth=1, min_leaf_size=2, random_seed=17).fit(logs)
    print("\nWang 2016: estimated discrete market-price mass")
    for region in ("north", "south"):
        estimate = tree.predict({"region": region})
        print(f"  region={region}: masses={estimate.masses}, tail={estimate.tail_probability:.3f}, "
              f"P(win at 3)={estimate.win_probability(3.0):.3f}")


if __name__ == "__main__":
    main()
