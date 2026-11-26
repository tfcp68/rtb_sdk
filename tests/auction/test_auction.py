"""
Root file of the test suite.

For each function from _functions.FUNCTIONS a describe_<func_name> block
(pytest-describe) is dynamically created, inside which the
parameterized test_it runs all cases from fixtures/cases/<func_name>.json.
"""
import sys
import pytest

from tests._helpers import cases, ids, run
from tests.auction._functions import FUNCTIONS


def _make_describe(func_name: str, _fn, _unpacker):
    _cases = cases(func_name, _unpacker)
    _ids = ids(_cases)

    def describe_fn():
        @pytest.mark.parametrize("case", _cases, ids=_ids)
        def test_it(case):
            run(_fn, case)

    describe_fn.__name__ = f"describe_{func_name}"
    describe_fn.__qualname__ = f"describe_{func_name}"
    return describe_fn


_this_module = sys.modules[__name__]
for _func_name, (_func, _unpacker) in FUNCTIONS.items():
    setattr(_this_module, f"describe_{_func_name}", _make_describe(_func_name, _func, _unpacker))
