"""Balance synthetic traffic, add a campaign and estimate a traffic reduction."""
from datetime import timedelta

from rtb_sdk.balancer.seasonal import (
    HistoricalLogsConfig,
    build_seasonal_context,
    seasonal_add_new_balanced_campaign,
    seasonal_balance_traffic,
)

from examples.sample_data import ensure_samples
from examples.temporal_balancer.fixtures import ADS, LOGS_CSV, PARAMS, PERIOD, TAG_COL_MAP


def build_context(ads: dict):
    config = HistoricalLogsConfig(path=str(LOGS_CSV), timestamp_col="ts", user_id_col="user_id",
                                  aggregation_mode="hour_of_day", timezone="UTC")
    return build_seasonal_context(config, ads, PERIOD, tag_col_map=TAG_COL_MAP)


def print_volumes(title: str, volumes: dict[str, int]) -> None:
    print(f"{title} (total: {sum(volumes.values()):,})")
    for ad_id, volume in sorted(volumes.items()):
        print(f"  {ad_id:<20} {volume:>7,}")


def main() -> None:
    ensure_samples()
    existing = {key: ad for key, ad in ADS.items() if key != "ad_mobile_new"}
    # Use the historical hourly profile to plan one day of synthetic traffic.
    daily_params = {**PARAMS, "period": {"period_start": PERIOD["period_start"],
                                       "period_end": PERIOD["period_start"] + timedelta(days=1)}}
    params = {**daily_params, "seasonal_context": build_context(existing)}
    distribution = seasonal_balance_traffic(existing, params)
    print_volumes("Traffic distribution:", distribution)

    result = seasonal_add_new_balanced_campaign(
        ADS, distribution, {**daily_params, "seasonal_context": build_context(ADS)})
    print_volumes("Distribution after adding a campaign:", result["report"])
    print_volumes("New campaign volumes:", result["new_ads_volumes"])

    reduced = seasonal_balance_traffic(existing, {**params, "total_traffic_volume": PARAMS["total_traffic_volume"] // 4})
    print_volumes("Distribution with one quarter of the traffic:", reduced)
    print_volumes("Change from the original distribution:",
                  {ad_id: reduced[ad_id] - distribution[ad_id] for ad_id in distribution})


if __name__ == "__main__":
    main()
