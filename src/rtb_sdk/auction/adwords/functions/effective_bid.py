def compute_effective_bid(cpm: float, price: float) -> float:
    """Computes the effective bid: cpm * (1 - price)."""
    return cpm * (1.0 - price)
