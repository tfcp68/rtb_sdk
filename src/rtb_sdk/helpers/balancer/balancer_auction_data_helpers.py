from rtb_sdk.schemas.balancer_schemas import BalancerAuctionData, OuterVocabs, ProjectedAdVolumes
from rtb_sdk.schemas.auction_schemas import AdId, VocabName, RawTag
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes


def is_valid_balancer_auction_data_vocabs(val) -> bool:
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


def is_valid_balancer_auction_data_tag_probabilities(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, dict):
            return False
        for raw_tag, prob in v.items():
            if not isinstance(raw_tag, str):
                return False
            if not isinstance(prob, (int, float)) or isinstance(prob, bool):
                return False
    return True


def is_valid_balancer_auction_data_ads_distribution(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, int) or isinstance(v, bool):
            return False
    return True


def is_valid_balancer_auction_data_ads_probabilities(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
    return True


def is_valid_balancer_auction_data_ads_total(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val >= 0


def is_valid_balancer_auction_data(val) -> bool:
    if not isinstance(val, dict):
        return False
    return (
        is_valid_balancer_auction_data_vocabs(val.get('vocabs'))
        and is_valid_balancer_auction_data_tag_probabilities(val.get('tag_probabilities'))
        and is_valid_balancer_auction_data_ads_distribution(val.get('ads_distribution'))
        and is_valid_balancer_auction_data_ads_probabilities(val.get('ads_probabilities'))
        and is_valid_balancer_auction_data_ads_total(val.get('ads_total'))
    )


def create_balancer_auction_data(
    vocabs: OuterVocabs = {},
    tag_probabilities: dict[VocabName, dict[RawTag, float]] = {},
    ads_distribution: ProjectedAdVolumes = {},
    ads_probabilities: dict[AdId, float] = {},
    ads_total: int = 0,
) -> BalancerAuctionData:
    validators: dict[str, tuple] = {
        'vocabs':            (vocabs,            is_valid_balancer_auction_data_vocabs,            f"Invalid vocabs: {vocabs!r}"),
        'tag_probabilities': (tag_probabilities, is_valid_balancer_auction_data_tag_probabilities, f"Invalid tag_probabilities: {tag_probabilities!r}"),
        'ads_distribution':  (ads_distribution,  is_valid_balancer_auction_data_ads_distribution,  f"Invalid ads_distribution: {ads_distribution!r}"),
        'ads_probabilities': (ads_probabilities, is_valid_balancer_auction_data_ads_probabilities, f"Invalid ads_probabilities: {ads_probabilities!r}"),
        'ads_total':         (ads_total,         is_valid_balancer_auction_data_ads_total,         f"Invalid ads_total: {ads_total!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)
    return BalancerAuctionData(
        vocabs=vocabs,
        tag_probabilities=tag_probabilities,
        ads_distribution=ads_distribution,
        ads_probabilities=ads_probabilities,
        ads_total=ads_total,
    )


def load_balancer_auction_data(data: dict) -> BalancerAuctionData:
    if not is_valid_balancer_auction_data(data):
        raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, f"Invalid BalancerAuctionData: {data!r}")
    return data  # type: ignore[return-value]


def get_balancer_auction_data_vocabs(
    data: BalancerAuctionData,
    default: OuterVocabs | None = None,
) -> OuterVocabs:
    return data.get('vocabs', default if default is not None else {})


def get_balancer_auction_data_tag_probabilities(
    data: BalancerAuctionData,
    default: dict[VocabName, dict[RawTag, float]] | None = None,
) -> dict[VocabName, dict[RawTag, float]]:
    return data.get('tag_probabilities', default if default is not None else {})


def get_balancer_auction_data_ads_distribution(
    data: BalancerAuctionData,
    default: ProjectedAdVolumes | None = None,
) -> ProjectedAdVolumes:
    return data.get('ads_distribution', default if default is not None else {})


def get_balancer_auction_data_ads_probabilities(
    data: BalancerAuctionData,
    default: dict[AdId, float] | None = None,
) -> dict[AdId, float]:
    return data.get('ads_probabilities', default if default is not None else {})


def get_balancer_auction_data_ads_total(
    data: BalancerAuctionData,
    default: int = 0,
) -> int:
    return data.get('ads_total', default)
