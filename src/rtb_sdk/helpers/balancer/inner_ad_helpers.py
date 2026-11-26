from typing import Optional

from rtb_sdk.schemas.balancer_schemas import InnerAd, ProjectedAdVolumes
from rtb_sdk.schemas.auction_schemas import Ad, AdId, VocabName, FullTag
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.constants.balancer_constants import MAX_VOL_UNLIMITED


def is_valid_inner_ad_id(val) -> bool:
    return isinstance(val, str) and len(val) > 0


def is_valid_inner_ad_targets(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, list):
            return False
        if not all(isinstance(t, str) for t in v):
            return False
    return True


def is_valid_inner_ad_min_vol(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val >= 0


def is_valid_inner_ad_max_vol(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def is_valid_inner_ad_price(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0


def is_valid_inner_ad_date_factor(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0


def is_valid_inner_ad_freq(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val > 0


def is_valid_inner_ad(val) -> bool:
    if not isinstance(val, dict):
        return False
    min_vol = val.get('min_vol')
    max_vol = val.get('max_vol')
    if not isinstance(min_vol, int) or isinstance(min_vol, bool) or min_vol < 0:
        return False
    if not isinstance(max_vol, int) or isinstance(max_vol, bool):
        return False
    if min_vol > max_vol:
        return False
    return (
        is_valid_inner_ad_id(val.get('id'))
        and is_valid_inner_ad_targets(val.get('targets'))
        and is_valid_inner_ad_price(val.get('price'))
        and is_valid_inner_ad_date_factor(val.get('date_factor'))
        and is_valid_inner_ad_freq(val.get('freq'))
    )


def create_inner_ad(
    id: AdId = 'EmptyAd',
    targets: dict[VocabName, list[FullTag]] = {},
    min_vol: int = 0,
    max_vol: int = 0,
    price: float = 0.0,
    date_factor: float = 1.0,
    freq: int = 1,
) -> InnerAd:
    validators: dict[str, tuple] = {
        'id':          (id,          is_valid_inner_ad_id,          f"Invalid id: {id!r}"),
        'targets':     (targets,     is_valid_inner_ad_targets,     f"Invalid targets: {targets!r}"),
        'min_vol':     (min_vol,     is_valid_inner_ad_min_vol,     f"Invalid min_vol: {min_vol!r}"),
        'max_vol':     (max_vol,     is_valid_inner_ad_max_vol,     f"Invalid max_vol: {max_vol!r}"),
        'price':       (price,       is_valid_inner_ad_price,       f"Invalid price: {price!r}"),
        'date_factor': (date_factor, is_valid_inner_ad_date_factor, f"Invalid date_factor: {date_factor!r}"),
        'freq':        (freq,        is_valid_inner_ad_freq,        f"Invalid freq: {freq!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)
    if min_vol > max_vol:
        raise BalancerError(
            ErrorCodes.INPUT_VALIDATION_ERROR,
            f"min_vol ({min_vol}) must be <= max_vol ({max_vol})",
        )
    return InnerAd(
        id=id,
        targets=targets,  # type: ignore[arg-type]
        min_vol=min_vol,
        max_vol=max_vol,
        price=price,
        date_factor=date_factor,
        freq=freq,
    )


def load_inner_ad(data: dict) -> InnerAd:
    if not is_valid_inner_ad(data):
        raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, f"Invalid InnerAd: {data!r}")
    return data  # type: ignore[return-value]


def ad_to_inner(ad: Ad) -> InnerAd:
    """Converts the public Ad into an InnerAd for LP optimization."""
    targets_value: dict[VocabName, list[str]] = ad.get('targets', {}).get('value', {})
    targets: dict[VocabName, list[FullTag]] = {
        vocab: [f'{vocab}:{tag}' for tag in tags]
        for vocab, tags in targets_value.items()
    }
    freq_limits_value: dict = ad.get('ad_frequency_limit', {}).get('value', {})
    freq = int(freq_limits_value.get('d', 0))
    volume = ad.get('volume', 0)
    # volume=0 per the spec means "no upper limit"; stored as MAX_VOL_UNLIMITED,
    # so as not to confuse it with "frozen at 0" in add_new_balanced_campaign (there min_vol=max_vol=0)
    max_vol = volume if volume > 0 else MAX_VOL_UNLIMITED
    # freq<=0 (field absent or 0) means "there is no daily frequency limit".
    # build_ads_real_volumes treats freq as a hard cap on volume, while InnerAd.freq must
    # be > 0 (validator), so "no limit" cannot be encoded as zero — otherwise the cap
    # would collapse the volume to freq=1. Stored as MAX_VOL_UNLIMITED (the cap does not bind),
    # symmetric to the handling of volume above.
    real_freq = freq if freq > 0 else MAX_VOL_UNLIMITED
    return create_inner_ad(
        id=ad.get('id', ''),
        targets=targets,
        min_vol=0,
        max_vol=max_vol,
        price=float(ad.get('cpm', 0.0)),
        date_factor=1.0,
        freq=real_freq,
    )


def get_inner_ad_id(ad: InnerAd, default: AdId = '') -> AdId:
    return ad.get('id', default)


def get_inner_ad_targets(
    ad: InnerAd,
    default: Optional[dict[VocabName, list[FullTag]]] = None,
) -> dict[VocabName, list[FullTag]]:
    return ad.get('targets', default if default is not None else {})  # type: ignore[return-value]


def get_inner_ad_min_vol(ad: InnerAd, default: Optional[int] = 0) -> Optional[int]:
    return ad.get('min_vol', default)


def get_inner_ad_max_vol(ad: InnerAd, default: Optional[int] = 0) -> Optional[int]:
    return ad.get('max_vol', default)


def get_inner_ad_price(ad: InnerAd, default: Optional[float] = 0.0) -> Optional[float]:
    return ad.get('price', default)


def get_inner_ad_date_factor(ad: InnerAd, default: Optional[float] = 1.0) -> Optional[float]:
    return ad.get('date_factor', default)


def get_inner_ad_freq(ad: InnerAd, default: Optional[int] = 1) -> Optional[int]:
    return ad.get('freq', default)


def build_ads_real_volumes(
    ads: dict[AdId, InnerAd],
    total_volume: int,
    ads_probabilities: dict[AdId, float],
) -> dict[AdId, float]:
    # Computes the real upper bound of traffic for each ad.
    # The final max is applied by three consecutive constraints:
    #
    #   flow_volume = total * P(ad) * date_factor
    #     — probabilistic volume: how much traffic statistically passes
    #       through the ad taking the time factor (seasonality) into account.
    #
    #   min(max_vol, flow_volume)
    #     — do not exceed the ad's contractual maximum.
    #
    #   min(..., freq)  (if freq > 0)
    #     — an additional hard cap by impression frequency. Applied before the LP,
    #       so that the solver optimizes within the frequency constraint right away.
    result: dict[AdId, float] = {}
    for ad_id, ad in ads.items():
        max_vol: int = get_inner_ad_max_vol(ad, default=0) or 0
        date_factor: float = get_inner_ad_date_factor(ad, default=1.0) or 1.0
        freq: int = get_inner_ad_freq(ad, default=0) or 0
        p = ads_probabilities.get(ad_id, 1.0)
        flow_volume = total_volume * p * date_factor
        real_max = min(max_vol, flow_volume)
        if freq > 0:
            real_max = min(real_max, freq)
        result[ad_id] = real_max
    return result


def balanced_frequency_limit(
    ads: dict[AdId, InnerAd],
    report: ProjectedAdVolumes,
) -> dict[AdId, int]:
    result: dict[AdId, int] = {}
    for ad_id in report:
        f: int = get_inner_ad_freq(ads[ad_id], default=1) or 1
        d = report[ad_id]
        result[ad_id] = min(f, d)
    return result
