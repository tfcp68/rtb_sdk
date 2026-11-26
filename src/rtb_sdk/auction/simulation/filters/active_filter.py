"""
Filter of ads by activity and campaign dates.
"""
from datetime import datetime

from rtb_sdk.schemas import AdsDict
from rtb_sdk.helpers import get_ad_active, get_ad_start_date, get_ad_end_date, get_ads_dict, create_ads_dict


def filter_by_active(
    ads: AdsDict,
    current_date: datetime,
) -> AdsDict:
    """
    Keeps only active ads whose campaign is running on the current date.

    Filter pass conditions:
      - ad['active'] == True
      - ad['start_date'] <= current_date <= ad['end_date']

    Args:
        ads: AdsDict of all ads
        current_date: current request time

    Returns:
        AdsDict: filtered dictionary of ads
    """
    result = {
        ad_id: ad
        for ad_id, ad in get_ads_dict(ads).items()
        if get_ad_active(ad)
        and get_ad_start_date(ad) <= current_date <= get_ad_end_date(ad)
    }
    return create_ads_dict(result)
