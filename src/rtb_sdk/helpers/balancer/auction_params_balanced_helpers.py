from rtb_sdk.schemas.balancer_schemas import AuctionParamsBalanced, BalancerAuctionData, OuterVocabs
from rtb_sdk.schemas.auction_schemas import VocabName, RawTag
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from .balancer_auction_data_helpers import is_valid_balancer_auction_data


def is_valid_parameters_balanced_request(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str) or not isinstance(v, str):
            return False
    return True


def is_valid_parameters_balanced_vocabs(val) -> bool:
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


def is_valid_parameters_balanced_balancer_data(val) -> bool:
    if val is None:
        return True
    return is_valid_balancer_auction_data(val)


def is_valid_parameters_balanced(val) -> bool:
    if not isinstance(val, dict):
        return False
    return (
        is_valid_parameters_balanced_request(val.get('request'))
        and is_valid_parameters_balanced_vocabs(val.get('vocabs'))
        and is_valid_parameters_balanced_balancer_data(val.get('balancer_data'))
    )


def create_parameters_balanced(
    request: dict[VocabName, RawTag] = {},
    vocabs: OuterVocabs = {},
    balancer_data: BalancerAuctionData | None = None,
) -> AuctionParamsBalanced:
    validators: dict[str, tuple] = {
        'request':       (request,       is_valid_parameters_balanced_request,       f"Invalid request: {request!r}"),
        'vocabs':        (vocabs,         is_valid_parameters_balanced_vocabs,        f"Invalid vocabs: {vocabs!r}"),
        'balancer_data': (balancer_data,  is_valid_parameters_balanced_balancer_data, f"Invalid balancer_data: {balancer_data!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)
    return AuctionParamsBalanced(
        request=request,
        vocabs=vocabs,
        balancer_data=balancer_data,
    )


def load_parameters_balanced(data: dict) -> AuctionParamsBalanced:
    if not is_valid_parameters_balanced(data):
        raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, f"Invalid AuctionParamsBalanced: {data!r}")
    return data  # type: ignore[return-value]


def get_parameters_balanced_request(
    params: AuctionParamsBalanced,
    default: dict[VocabName, RawTag] | None = None,
) -> dict[VocabName, RawTag]:
    return params.get('request', default if default is not None else {})


def get_parameters_balanced_vocabs(
    params: AuctionParamsBalanced,
    default: OuterVocabs | None = None,
) -> OuterVocabs:
    return params.get('vocabs', default if default is not None else {})


def get_parameters_balanced_balancer_data(
    params: AuctionParamsBalanced,
    default: BalancerAuctionData | None = None,
) -> BalancerAuctionData | None:
    return params.get('balancer_data', default)
