from rtb_sdk.schemas.balancer_schemas import RequestFlow, RequestFlowWithAd
from rtb_sdk.schemas.auction_schemas import AdId, FullTag
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes


def is_valid_category_tags(val) -> bool:
    return isinstance(val, tuple) and all(isinstance(t, str) for t in val)


def is_valid_category_probability(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and 0 <= val <= 1


def is_valid_category(val) -> bool:
    if not isinstance(val, dict):
        return False
    return (
        is_valid_category_tags(val.get('tags'))
        and is_valid_category_probability(val.get('probability'))
    )


def create_category(
    tags: tuple[FullTag, ...] = (),
    probability: float = 0.0,
) -> RequestFlow:
    validators: dict[str, tuple] = {
        'tags':        (tags,        is_valid_category_tags,        f"Invalid tags: {tags!r}"),
        'probability': (probability, is_valid_category_probability, f"Invalid probability: {probability!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)
    return RequestFlow(tags=tags, probability=probability)  # type: ignore[arg-type]


def load_category(data: dict) -> RequestFlow:
    if not is_valid_category(data):
        raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, f"Invalid RequestFlow: {data!r}")
    return data  # type: ignore[return-value]


def is_valid_internal_category_ad_id(val) -> bool:
    return isinstance(val, str) and len(val) > 0


def is_valid_internal_category(val) -> bool:
    if not isinstance(val, dict):
        return False
    return (
        is_valid_category_tags(val.get('tags'))
        and is_valid_category_probability(val.get('probability'))
        and is_valid_internal_category_ad_id(val.get('ad_id'))
    )


def create_internal_category(
    tags: tuple[FullTag, ...] = (),
    probability: float = 0.0,
    ad_id: AdId = 'EmptyAd',
) -> RequestFlowWithAd:
    validators: dict[str, tuple] = {
        'tags':        (tags,        is_valid_category_tags,           f"Invalid tags: {tags!r}"),
        'probability': (probability, is_valid_category_probability,    f"Invalid probability: {probability!r}"),
        'ad_id':       (ad_id,       is_valid_internal_category_ad_id, f"Invalid ad_id: {ad_id!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)
    return RequestFlowWithAd(tags=tags, probability=probability, ad_id=ad_id)  # type: ignore[arg-type]


def load_internal_category(data: dict) -> RequestFlowWithAd:
    if not is_valid_internal_category(data):
        raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, f"Invalid RequestFlowWithAd: {data!r}")
    return data  # type: ignore[return-value]


def get_category_tags(cat: RequestFlow) -> tuple[FullTag, ...]:
    return cat.get('tags', ())


def get_category_probability(cat: RequestFlow, default: float = 0.0) -> float:
    return cat.get('probability', default)


def get_internal_category_tags(cat: RequestFlowWithAd) -> tuple[FullTag, ...]:
    return cat.get('tags', ())


def get_internal_category_probability(cat: RequestFlowWithAd, default: float = 0.0) -> float:
    return cat.get('probability', default)


def get_internal_category_ad_id(cat: RequestFlowWithAd, default: AdId = '') -> AdId:
    return cat.get('ad_id', default)
