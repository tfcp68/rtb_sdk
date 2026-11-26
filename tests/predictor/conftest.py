"""
Pytest fixtures for the predictor tests.
"""
import os
import pickle
import shutil
from pathlib import Path

import pytest

from tests.predictor._helpers import (
    make_predictor_data,
    make_fit_data,
    make_test_data,
    make_result_test_data,
    make_common_model,
    make_model_options,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"
TMP_DIR = Path(__file__).parent / "tmp"


@pytest.fixture(scope="session", autouse=True)
def setup_predictor_fixtures():
    """Creates fixture files needed by JSON test cases."""
    FIXTURES_DIR.mkdir(exist_ok=True)
    TMP_DIR.mkdir(exist_ok=True)

    # Create pkl model fixture (any picklable dict)
    model_pkl = FIXTURES_DIR / "sample_model.pkl"
    if not model_pkl.exists():
        model = {"model": None, "model_type": "prophet", "__type": "ProphetModel"}
        with open(model_pkl, "wb") as f:
            pickle.dump(model, f)

    yield

    # Cleanup tmp directory after all tests
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR, ignore_errors=True)


@pytest.fixture
def predictor_data():
    return make_predictor_data()


@pytest.fixture
def fit_data():
    return make_fit_data()


@pytest.fixture
def test_data():
    return make_test_data()


@pytest.fixture
def result_test_data():
    return make_result_test_data()


@pytest.fixture
def common_model():
    return make_common_model()


@pytest.fixture
def model_options():
    return make_model_options()