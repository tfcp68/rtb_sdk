"""
Auction data loaders from files.

Used by the simulation and tests to load ads, requests
and tag dictionaries from JSON and CSV files.
"""
import csv
import json
from datetime import datetime
from typing import Any

from rtb_sdk.schemas import AdsDict, Request, TargetVector, VocabName

from rtb_sdk.helpers import (
    load_ad_raw,
    create_ads_dict,
    create_request,
    get_request_date,
    create_request_tags,
    create_target_vector,
    get_target_vector_dict,
)


# ── date parsing ───────────────────────────────────────────────────────────────

def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


# ── loaders ────────────────────────────────────────────────────────────────────

def load_ads_from_json(path: str) -> AdsDict:
    """
    Loads ads from a JSON file.

    Accepted formats:
      - list of Ad objects: [{...}, {...}]
      - dictionary {ad_id → Ad}: {ad_id: {...}}
      - wrapper {'__type': 'AdsDict', 'value': {...}}

    Args:
        path: path to the JSON file

    Returns:
        AdsDict: key = ad['id']
    """
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and data.get('__type') == 'AdsDict':
        items = list(data.get('value', {}).values())
    elif isinstance(data, dict):
        items = list(data.values())
    else:
        items = list(data)

    ads = {}
    for item in items:
        ad = load_ad_raw(item)
        ads[str(item.get('id', ''))] = ad

    return create_ads_dict(ads)


def load_requests_from_json(path: str) -> list[Request]:
    """
    Loads requests from a JSON file.

    Expected format: a list of objects with the fields:
      - client_id (str) → user_id
      - date (str ISO 8601) → datetime
      - tags (dict {vocab_name → raw_tag}) → RequestTags

    Args:
        path: path to the JSON file

    Returns:
        list[Request]: in the same order as in the file
    """
    with open(path) as f:
        data = json.load(f)

    requests = []
    for i, item in enumerate(data):
        date = _parse_datetime(item.get('date', ''))
        tags = create_request_tags(item.get('tags', {}))
        req = create_request(
            id=str(i),
            user_id=str(item.get('client_id', 'EmptyUser')),
            date=date,
            tags=tags,
        )
        requests.append(req)
    return requests


def load_requests_from_csv(
    path: str,
    vocabs: TargetVector,
) -> list[Request]:
    """
    Loads requests from a CSV file (wide format).

    Expected CSV format:
      client_id, date, <vocab1_name>, <vocab2_name>, ...

    Column names (except client_id and date) are matched to the vocabs keys.
    Empty cells → the vocab is absent from the request tags.

    Args:
        path: path to the CSV file
        vocabs: TargetVector with tag dictionaries;
                used to determine the columns

    Returns:
        list[Request]: in the order of rows in the file
    """
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    vocab_names = set(get_target_vector_dict(vocabs).keys())
    requests = []
    for i, row in enumerate(rows):
        date = _parse_datetime(row.get('date', ''))
        tags: dict[VocabName, str] = {}
        for col, value in row.items():
            if col in vocab_names and value:
                tags[col] = value
        req = create_request(
            id=str(i),
            user_id=str(row.get('client_id', 'EmptyUser')),
            date=date,
            tags=create_request_tags(tags),
        )
        requests.append(req)
    return requests


def load_vocabs_from_json(path: str) -> TargetVector:
    """
    Loads tag dictionaries from a JSON file.

    Expected format: {vocab_name: [raw_tag, ...]}.

    Args:
        path: path to the JSON file

    Returns:
        TargetVector: tag dictionaries
    """
    with open(path) as f:
        return create_target_vector(json.load(f))


def sort_request(requests: list[Request]) -> list[Request]:
    """
    Sorts requests by date for chronological replay.

    Args:
        requests: list of loaded requests

    Returns:
        list[Request]: requests sorted by ascending date
    """
    return sorted(requests, key=lambda r: get_request_date(r))
