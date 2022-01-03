import numpy as np
import pytest

from pandas._libs.tslibs.timedeltas import delta_to_nanoseconds

from pandas import (
    Timedelta,
    offsets,
)


@pytest.mark.parametrize(
    "obj,expected",
    [
        (np.timedelta64(14, "D"), 14 * 24 * 3600 * 1e9),
        (Timedelta(minutes=-7), -7 * 60 * 1e9),
        (Timedelta(minutes=-7).to_pytimedelta(), -7 * 60 * 1e9),
        (Timedelta(seconds=1234e-9), 1234),  # GH43764, GH40946
        (
            Timedelta(seconds=1e-9, milliseconds=1e-5, microseconds=1e-1),
            111,
        ),  # GH43764
        (
            Timedelta(days=1, seconds=1e-9, milliseconds=1e-5, microseconds=1e-1),
            24 * 3600e9 + 111,
        ),  # GH43764
        (offsets.Nano(125), 125),
        (1, 1),
        (np.int64(2), 2),
        (np.int32(3), 3),
    ],
)
def test_delta_to_nanoseconds(obj, expected):
    result = delta_to_nanoseconds(obj)
    assert result == expected


def test_delta_to_nanoseconds_error():
    obj = np.array([123456789], dtype="m8[ns]")

    with pytest.raises(TypeError, match="<class 'numpy.ndarray'>"):
        delta_to_nanoseconds(obj)


def test_huge_nanoseconds_overflow():
    # GH 32402
    assert delta_to_nanoseconds(Timedelta(1e10)) == 1e10
    assert delta_to_nanoseconds(Timedelta(nanoseconds=1e10)) == 1e10


# GH40946
@pytest.mark.parametrize(
    "obj, expected_ns, expected_us",
    [
        (Timedelta("1us"), 1e-6, 1e-6),
        (Timedelta("500ns"), 5e-7, 0.0),
        (Timedelta(nanoseconds=500), 5e-7, 0.0),
        (Timedelta(seconds=1, nanoseconds=500), 1 + 5e-7, 1.0),
        (Timedelta(seconds=1e-9, milliseconds=1e-5, microseconds=1e-1), 111e-9, 0.0),
        (
            Timedelta(days=1, seconds=1e-9, milliseconds=1e-5, microseconds=1e-1),
            24 * 3600 + 111e-9,
            24 * 3600,
        ),
    ],
)
def test_total_seconds(obj: Timedelta, expected_ns, expected_us):
    assert obj.total_seconds() == expected_us
    assert obj.total_seconds(ns_precision=True) == expected_ns
