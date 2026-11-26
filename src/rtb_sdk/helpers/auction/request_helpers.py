from rtb_sdk.schemas import (
    Request,
    RequestId,
    UserId,
    RequestTags,
)
from rtb_sdk.constants import DataAuctionType, DATE_ZERO
from datetime import datetime
from rtb_sdk.errors import AuctionError, ErrorCodes
from .request_tags_helpers import is_valid_request_tags, create_request_tags, load_request_tags
from ..type_helpers import check_type


def is_valid_request(val) -> bool:
    if not check_type(val, 'Request'):
        return False
    if not is_valid_request_id(get_request_id(val)):
        return False
    if not is_valid_user_id(get_request_user_id(val)):
        return False
    if not is_valid_request_date(get_request_date(val)):
        return False
    if not is_valid_request_tags(get_request_tags(val)):
        return False
    return True


def is_valid_request_id(val) -> bool:
    return isinstance(val, str)

def is_valid_user_id(val) -> bool:
    return isinstance(val, str)

def is_valid_request_date(val) -> bool:
    return isinstance(val, datetime)


def create_request(
        id: RequestId = 'EmptyRequest',
        user_id: UserId = 'EmptyUser',
        date: datetime = DATE_ZERO,
        tags: RequestTags = create_request_tags(),
) -> Request:
    validators: dict[str, tuple] = {
        'id':      (id,      is_valid_request_id,   f"Invalid request id: {id!r}"),
        'user_id': (user_id, is_valid_user_id,       f"Invalid user_id: {user_id!r}"),
        'date':    (date,    is_valid_request_date,  f"Invalid date: {date!r}"),
        'tags':    (tags,    is_valid_request_tags,  f"Invalid tags: {tags!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, error_msg)
    request: Request = {
        '__type': DataAuctionType.REQUEST,
        'id': id,
        'user_id': user_id,
        'date': date,
        'tags': tags,
    }
    return request


def load_request(data: dict) -> Request:
    if not check_type(data, 'Request'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for Request: {data!r}")
    if not is_valid_request_id(data.get('id')):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid request id: {data.get('id')!r}")
    if not is_valid_user_id(data.get('user_id')):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid user_id: {data.get('user_id')!r}")
    if not is_valid_request_date(data.get('date')):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid date: {data.get('date')!r}")
    load_request_tags(data.get('tags', {}))
    return data  # type: ignore[return-value]


def get_request_id(request: Request, default: RequestId = 'EmptyRequest') -> RequestId:
    return request.get('id', default)

def get_request_user_id(request: Request, default: UserId = 'EmptyUser') -> UserId:
    return request.get('user_id', default)

def get_request_date(request: Request, default: datetime = DATE_ZERO) -> datetime:
    return request.get('date', default)

def get_request_tags(request: Request, default: RequestTags = create_request_tags()) -> RequestTags:
    return request.get('tags', default)
