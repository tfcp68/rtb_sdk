"""
Generation of reports from auction simulation results.

Analogue of old/io_funcs/from_logs/report_creation.py for the new test system.
Supports the full report creation cycle:
  initialization → periodic updates → finalization → saving files.

Typical call order:
  vocab_stats = get_vocab_stats(vocabs, requests)
  report = create_report_dict(ads, flow_size, vocab_stats, name)

  for req in requests:
      for ad in ads_dict.values():
          update_report_with_request_tags(report, ad, req)
      ...simulation...
      if n % step == 0:
          update_report(driver, report, shown, date)

  update_report(driver, report, shown, date)
  finish_report(driver, report, uniq_users)
  save_report(report, output_dir)
  save_logs(request_to_ad, output_dir)
  make_gisto(uniq_users, output_dir)

Report files (by default in report/):
  - report.json                  — the main JSON report
  - logs.csv                     — request_id → ad_id mapping
  - requests_distribution.csv   — histogram of distribution across users
  - requests_histogram.png      — PNG histogram
"""

import csv
import datetime
import json
import os
from typing import TypedDict, cast

import matplotlib.pyplot as plt

from rtb_sdk.helpers import (
    get_ad_id,
    get_ad_volume,
    get_ad_price,
    get_ad_start_date,
    get_ad_end_date,
    get_ad_targetvector,
    get_ad_frequency_limit,
    get_ads_dict,
    get_fulltags,
    get_full_tag_vector_dict,
    get_target_vector_dict,
    build_full_tag,
    get_request_tags,
    get_request_tags_dict,
    get_frequency_limits_dict,
)
from rtb_sdk.schemas import AdsDict, Ad, AdId, Request, TargetVector
from rtb_sdk.constants import AuctionType, TAG_EMPTY
from rtb_sdk.auction.simulation.driver.driver import MockDriver
from rtb_sdk.auction.simulation.driver.driver import get_ad_total_counts as _driver_get_ad_total_counts


# ── report types ──────────────────────────────────────────────────────────────

class AdReportInfo(TypedDict):
    goal: int
    targets: dict
    ad_frequency_limit: dict
    target_requests_in_flow: int
    fuzzy_percent: float
    result: int
    utilization: float
    cpm: float
    start_date: datetime.datetime
    end_date: datetime.datetime


class PeriodStatistics(TypedDict):
    total_by_ads_percent: dict[AdId, float]
    precise_by_ads_percent: dict[AdId, float]
    fuzzy_by_ads_percent: dict[AdId, float]
    hit: int
    precise: int
    fuzzy: int
    miss: int
    total_progress: float
    sellout: float


class ReportPeriod(TypedDict):
    date: datetime.datetime
    statistics: PeriodStatistics


class ReportHeader(TypedDict):
    id: int
    title: str
    description: str
    version: float
    date: datetime.datetime
    flow_size: int
    shown_in_flow: int
    rejected_in_flow: int
    total_goal: int
    total_result: int
    utilization: float
    sellout: float
    uniq_users: int
    ads: dict[AdId, AdReportInfo]
    tag_stats: dict[str, dict[str, int]]


class ReportDict(TypedDict):
    header: ReportHeader
    periods: list[ReportPeriod]


# ── field names ───────────────────────────────────────────────────────────────

HEADER_FIELD           = 'header'
STATISTICS_FIELD       = 'statistics'
ID_FIELD               = 'id'
TITLE_FIELD            = 'title'
DESCRIPTION_FIELD      = 'description'
VERSION_FIELD          = 'version'
DATE_FIELD             = 'date'
FLOW_SIZE_FIELD        = 'flow_size'
SHOWN_IN_FLOW_FIELD    = 'shown_in_flow'
REJECTED_IN_FLOW_FIELD = 'rejected_in_flow'
ADS_FIELD              = 'ads'
UNIQ_USERS_FIELD       = 'uniq_users'
GOAL_FIELD             = 'goal'
TAGS_FIELD             = 'targets'
TARGET_IN_FLOW_FIELD   = 'target_requests_in_flow'
FUZZY_PERCENT_FIELD    = 'fuzzy_percent'
RESULT_FIELD           = 'result'
UTILIZATION_FIELD      = 'utilization'
PRICE_FIELD            = 'cpm'
START_DATE_FIELD       = 'start_date'
END_DATE_FIELD         = 'end_date'
TOTAL_GOAL_FIELD       = 'total_goal'
TOTAL_RESULT_FIELD     = 'total_result'
SELLOUT_FIELD          = 'sellout'
TAG_STATS_FIELD        = 'tag_stats'
PERIODS_FIELD          = 'periods'

TOTAL_BY_ADS_PERCENT   = 'total_by_ads_percent'
PRECISE_BY_ADS_PERCENT = 'precise_by_ads_percent'
FUZZY_BY_ADS_PERCENT   = 'fuzzy_by_ads_percent'

HIT_FIELD            = 'hit'
PRECISE_FIELD        = AuctionType.PRECISE   # 'precise'
FUZZY_FIELD          = AuctionType.FUZZY     # 'fuzzy'
MISS_FIELD           = 'miss'
TOTAL_PROGRESS_FIELD = 'total_progress'

AD_FREQ_LIMIT_FIELD   = 'ad_frequency_limit'
USER_FREQ_LIMIT_FIELD = 'user_frequency_limit'


# ── internal helpers ──────────────────────────────────────────────────────────

def _get_ad_total_counts(
    driver: MockDriver,
    ad_id: str,
) -> tuple[int, int]:
    """Returns (precise_count, fuzzy_count) in total over the whole simulation time."""
    counts = _driver_get_ad_total_counts(driver, [ad_id]).get(ad_id, {})
    precise = counts.get(AuctionType.PRECISE, 0)
    fuzzy = counts.get(AuctionType.FUZZY, 0)
    return precise, fuzzy


def _datetime_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _ad_target_full_tag_sets(ad: Ad) -> dict[str, set[str]]:
    """Returns {vocab → set(full_tag)} from the ad's targets."""
    ftv = get_fulltags(get_ad_targetvector(ad))
    return {vocab: set(tags) for vocab, tags in get_full_tag_vector_dict(ftv).items()}


def _request_full_tag_sets(request: Request) -> dict[str, set[str]]:
    """Returns {vocab → {full_tag}} from the request tags."""
    return {
        vocab: {ft}
        for vocab, ft in get_request_tags_dict(get_request_tags(request)).items()
    }


# ── public API ────────────────────────────────────────────────────────────────

def create_report_dict(
    ads: AdsDict,
    flow_size: int,
    vocab_stats: dict,
    name: str,
) -> ReportDict:
    """
    Creates the initial report dictionary.

    Args:
        ads: AdsDict — all ads of the simulation
        flow_size: total number of requests in the flow
        vocab_stats: {vocab_name → {full_tag → count}} from get_vocab_stats()
        name: simulation name (goes into header.title)

    Returns:
        dict: initialized report
    """
    ads_dict = get_ads_dict(ads)

    res: dict = {
        HEADER_FIELD: {
            ID_FIELD:               0,
            TITLE_FIELD:            name,
            DESCRIPTION_FIELD:      'Auction simulation',
            VERSION_FIELD:          0.1,
            DATE_FIELD:             datetime.datetime.now(),
            FLOW_SIZE_FIELD:        flow_size,
            SHOWN_IN_FLOW_FIELD:    0,
            REJECTED_IN_FLOW_FIELD: 0,
            TOTAL_GOAL_FIELD:       0,
            TOTAL_RESULT_FIELD:     0,
            UTILIZATION_FIELD:      0,
            SELLOUT_FIELD:          0,
            UNIQ_USERS_FIELD:       0,
            ADS_FIELD:              {},
            TAG_STATS_FIELD:        vocab_stats,
        },
        PERIODS_FIELD: [],
    }

    total_volume = 0
    for ad_id, ad in ads_dict.items():
        volume = get_ad_volume(ad)
        total_volume += volume

        # targets with frequencies from vocab_stats: {vocab → {full_tag → count}}
        ftv_dict = get_full_tag_vector_dict(get_fulltags(get_ad_targetvector(ad)))
        targets_with_stats = {
            vocab: {ft: vocab_stats.get(vocab, {}).get(ft, 0) for ft in full_tags}
            for vocab, full_tags in ftv_dict.items()
        }

        res[HEADER_FIELD][ADS_FIELD][ad_id] = {
            GOAL_FIELD:            volume,
            TAGS_FIELD:            targets_with_stats,
            AD_FREQ_LIMIT_FIELD:   get_frequency_limits_dict(get_ad_frequency_limit(ad)),
            TARGET_IN_FLOW_FIELD:  0,
            FUZZY_PERCENT_FIELD:   0,
            RESULT_FIELD:          0,
            UTILIZATION_FIELD:     0,
            PRICE_FIELD:           get_ad_price(ad),
            START_DATE_FIELD:      get_ad_start_date(ad),
            END_DATE_FIELD:        get_ad_end_date(ad),
        }

    res[HEADER_FIELD][TOTAL_GOAL_FIELD] = total_volume
    return cast(ReportDict, res)


def update_report(
    driver: MockDriver,
    res: ReportDict,
    shown: int,
    date: datetime.datetime,
) -> ReportDict:
    """
    Adds a periodic statistics snapshot to the report.

    Called every N requests during the simulation and necessarily at the end.

    Args:
        driver: MockDriver
        res: current report
        shown: number of requests processed so far
        date: current time (time of the last request in the period)

    Returns:
        dict: updated report with the added period
    """
    new_period: dict = {
        DATE_FIELD: date,
        STATISTICS_FIELD: {
            TOTAL_BY_ADS_PERCENT:   {},
            PRECISE_BY_ADS_PERCENT: {},
            FUZZY_BY_ADS_PERCENT:   {},
        },
    }

    all_total = all_precise = all_fuzzy = 0

    for ad_id in res[HEADER_FIELD][ADS_FIELD]:
        volume  = res[HEADER_FIELD][ADS_FIELD][ad_id][GOAL_FIELD]
        precise, fuzzy = _get_ad_total_counts(driver, ad_id)
        total   = precise + fuzzy

        all_total   += total
        all_precise += precise
        all_fuzzy   += fuzzy

        new_period[STATISTICS_FIELD][TOTAL_BY_ADS_PERCENT][ad_id]   = total   / volume if volume else 0.0
        new_period[STATISTICS_FIELD][PRECISE_BY_ADS_PERCENT][ad_id] = precise / volume if volume else 0.0
        new_period[STATISTICS_FIELD][FUZZY_BY_ADS_PERCENT][ad_id]   = fuzzy   / volume if volume else 0.0

    new_period[STATISTICS_FIELD][HIT_FIELD]            = all_total
    new_period[STATISTICS_FIELD][PRECISE_FIELD]        = all_precise
    new_period[STATISTICS_FIELD][FUZZY_FIELD]          = all_fuzzy
    new_period[STATISTICS_FIELD][MISS_FIELD]           = shown - all_total
    new_period[STATISTICS_FIELD][TOTAL_PROGRESS_FIELD] = shown / res[HEADER_FIELD][FLOW_SIZE_FIELD]
    new_period[STATISTICS_FIELD][SELLOUT_FIELD]        = all_total / shown if shown else 0.0

    res[PERIODS_FIELD].append(cast(ReportPeriod, new_period))
    return res


def finish_report(
    driver: MockDriver,
    res: ReportDict,
    uniq_users: dict,
) -> ReportDict:
    """
    Finalizes the report after the simulation completes.

    Computes the final utilization, fuzzy share and sellout at the header level.
    Called after the last update_report().

    Args:
        driver: MockDriver
        res: report from update_report()
        uniq_users: {user_id → number of requests of the user}

    Returns:
        dict: final report
    """
    if not res[PERIODS_FIELD]:
        return res

    last_stats = res[PERIODS_FIELD][-1][STATISTICS_FIELD]

    res[HEADER_FIELD][SHOWN_IN_FLOW_FIELD]    = last_stats[HIT_FIELD]
    res[HEADER_FIELD][REJECTED_IN_FLOW_FIELD] = last_stats[MISS_FIELD]
    res[HEADER_FIELD][SELLOUT_FIELD] = (
        last_stats[HIT_FIELD] / res[HEADER_FIELD][FLOW_SIZE_FIELD]
        if res[HEADER_FIELD][FLOW_SIZE_FIELD] else 0.0
    )
    res[HEADER_FIELD][UNIQ_USERS_FIELD] = len(uniq_users)

    all_total = 0
    for ad_id in res[HEADER_FIELD][ADS_FIELD]:
        precise, fuzzy = _get_ad_total_counts(driver, ad_id)
        total    = precise + fuzzy
        all_total += total

        goal             = res[HEADER_FIELD][ADS_FIELD][ad_id][GOAL_FIELD]
        target_in_flow   = res[HEADER_FIELD][ADS_FIELD][ad_id][TARGET_IN_FLOW_FIELD]

        res[HEADER_FIELD][ADS_FIELD][ad_id][RESULT_FIELD]       = total
        res[HEADER_FIELD][ADS_FIELD][ad_id][FUZZY_PERCENT_FIELD] = fuzzy / total if total else 0.0

        if target_in_flow != 0:
            res[HEADER_FIELD][ADS_FIELD][ad_id][UTILIZATION_FIELD] = (
                total / min(target_in_flow, goal)
            )
        elif total != 0:
            res[HEADER_FIELD][ADS_FIELD][ad_id][UTILIZATION_FIELD] = -1.0
        else:
            res[HEADER_FIELD][ADS_FIELD][ad_id][UTILIZATION_FIELD] = 1.0

    res[HEADER_FIELD][TOTAL_RESULT_FIELD] = all_total
    total_goal = res[HEADER_FIELD][TOTAL_GOAL_FIELD]
    res[HEADER_FIELD][UTILIZATION_FIELD] = all_total / total_goal if total_goal else 0.0

    return res


def get_vocab_stats(vocabs: TargetVector, requests: list) -> dict:
    """
    Builds tag frequency statistics over the request flow.

    For each vocab counts how many times each full_tag occurs
    among the requests. If a request has no tag for the vocab, an empty tag is counted.

    Args:
        vocabs: TargetVector with tag dictionaries
        requests: list of Request

    Returns:
        dict: {vocab_name → {full_tag → count}}, sorted in descending order
    """
    res: dict = {}
    vocabs_dict = get_target_vector_dict(vocabs)
    for vocab_name, raw_tags in vocabs_dict.items():
        res[vocab_name] = {build_full_tag(vocab_name, rt): 0 for rt in raw_tags}

    empty_suffix = TAG_EMPTY  # ':_'

    for req in requests:
        tags_dict = get_request_tags_dict(get_request_tags(req))
        for vocab_name in vocabs_dict:
            if vocab_name not in tags_dict:
                empty_tag = vocab_name + empty_suffix
                res[vocab_name][empty_tag] = res[vocab_name].get(empty_tag, 0) + 1
            else:
                full_tag = tags_dict[vocab_name]
                res[vocab_name][full_tag] = res[vocab_name].get(full_tag, 0) + 1

    for vocab_name in res:
        res[vocab_name] = dict(
            sorted(res[vocab_name].items(), key=lambda kv: kv[1], reverse=True)
        )

    return res


def update_report_with_request_tags(report: ReportDict, ad: Ad, request: Request) -> None:
    """
    Updates the target_requests_in_flow counter for the ad in the report.

    Precise logic: for each vocab from the ad's targets the request must
    have a tag with an intersection. An ad without targets is compatible with any request.

    Args:
        report: current report (mutated in place)
        ad: Ad object
        request: Request object
    """
    ad_id = get_ad_id(ad)
    ad_tag_sets = _ad_target_full_tag_sets(ad)

    if not ad_tag_sets:
        # an ad without targeting fits any request
        report[HEADER_FIELD][ADS_FIELD][ad_id][TARGET_IN_FLOW_FIELD] += 1
        return

    req_tag_sets = _request_full_tag_sets(request)
    for vocab, ad_tags in ad_tag_sets.items():
        if not (ad_tags & req_tag_sets.get(vocab, set())):
            return

    report[HEADER_FIELD][ADS_FIELD][ad_id][TARGET_IN_FLOW_FIELD] += 1


def save_report(res: ReportDict, output_dir: str = 'report') -> None:
    """
    Saves the JSON report.

    Args:
        res: final report from finish_report()
        output_dir: folder to save to (created if needed)
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'report.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(res, f, default=_datetime_serializer, indent=4, ensure_ascii=False)
    print(f"Report saved: {path}")


def save_logs(request_to_ad: dict, output_dir: str = 'report') -> None:
    """
    Saves the CSV log of the request_id → ad_id mapping.

    Args:
        request_to_ad: {request_id → ad_id} (value -1 on MISS)
        output_dir: folder to save to
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'logs.csv')
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['request_id', 'ad_id'])
        for req_id, ad_id in request_to_ad.items():
            writer.writerow([req_id, ad_id])
    print(f"Logs saved: {path}")


def make_gisto(users: dict, output_dir: str = 'report') -> None:
    """
    Generates a CSV and PNG of the distribution of users by number of requests.

    Args:
        users: {user_id → number of requests}
        output_dir: folder to save to
    """
    os.makedirs(output_dir, exist_ok=True)

    # {number of requests → number of users}
    distribution: dict[int, int] = {}
    max_amount = 0
    for amount in users.values():
        max_amount = max(amount, max_amount)
        distribution[amount] = distribution.get(amount, 0) + 1

    for i in range(1, max_amount):
        if i not in distribution:
            distribution[i] = 0

    # CSV
    csv_path = os.path.join(output_dir, 'requests_distribution.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['requests_count', 'users_count'])
        for count, users_count in sorted(distribution.items()):
            writer.writerow([count, users_count])
    print(f"Distribution saved: {csv_path}")

    # PNG
    png_path = os.path.join(output_dir, 'requests_histogram.png')
    fig, ax = plt.subplots(figsize=(10, 6))
    keys   = list(distribution.keys())
    values = list(distribution.values())
    ax.bar(keys, values, color='skyblue', edgecolor='black')
    ax.set_xlabel('Number of requests')
    ax.set_ylabel('Number of users')
    ax.set_title('Distribution of users by number of requests')
    ax.grid(axis='y', alpha=0.75)
    for x, y in zip(keys, values):
        ax.text(x, y + 0.5, str(y), ha='center')
    fig.tight_layout()
    fig.savefig(png_path)
    plt.close(fig)
    print(f"Histogram saved: {png_path}")
