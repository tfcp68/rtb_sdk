from rtb_sdk.helpers import (
    create_ad,
    get_ad_id,
    create_auction_stats,
    create_granulated_counter,
    create_frequency_limits,
    create_ads_dict,
    create_ad_stats,
)


test_ad1 = create_ad(id="ad1",
                cpm=1000,
                priority=1,
                volume=1000,
                ad_frequency_limit=create_frequency_limits(
                    ten_minutes=1000, hour=1000, day=1000, week=1000, month=1000, min_interval=0
                ),
                )
test_ad2 = create_ad(id="ad2",
                cpm=500,
                priority=1,
                volume=200,
                ad_frequency_limit=create_frequency_limits(
                    ten_minutes=200, hour=200, day=200, week=200, month=200, min_interval=0
                ),
                )

test_ads1 = create_ads_dict({
    get_ad_id(test_ad1): test_ad1,
    get_ad_id(test_ad2): test_ad2,
})

test_stats1 = create_ad_stats(value={
    get_ad_id(test_ad1): create_auction_stats(
        create_granulated_counter(6, 6, 6, 6, 6)
    ),
    get_ad_id(test_ad2): create_auction_stats(
        create_granulated_counter(1, 1, 1, 1, 1)
    ),
})
