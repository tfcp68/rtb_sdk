from rtb_sdk.constants import SelectionFunc
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.auction.auction import auction
from examples.auction.fixtures import test_ads1, test_stats1


params = create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_ONE,
    ads_stats=test_stats1,
)

ad = auction(ads=test_ads1, parameters=params)
print(ad)
