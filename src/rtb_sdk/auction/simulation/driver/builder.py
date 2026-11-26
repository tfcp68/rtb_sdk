"""
Factory functions for creating a MockDriver.
"""
from rtb_sdk.schemas import AdsDict, TargetVector

from rtb_sdk.auction.simulation.statistics.mock_statistics import create_mock_statistics
from rtb_sdk.auction.simulation.driver.driver import MockDriver


def create_mock_driver(
    ads: AdsDict,
    vocabs: TargetVector,
) -> MockDriver:
    """
    Creates a MockDriver with the given ads and tag dictionaries.

    Initializes an empty MockStatistics.

    Args:
        ads: AdsDict of ads
        vocabs: TargetVector with tag dictionaries

    Returns:
        MockDriver: ready to use in the simulation loop
    """
    return {
        'ads': ads,
        'vocabs': vocabs,
        'stats': create_mock_statistics(),
    }
