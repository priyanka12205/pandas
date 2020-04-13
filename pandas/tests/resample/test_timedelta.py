from datetime import timedelta

import numpy as np
import pytest

import pandas as pd
from pandas import DataFrame, Series
import pandas._testing as tm
from pandas.core.indexes.timedeltas import timedelta_range


def test_asfreq_bug():
    df = DataFrame(data=[1, 3], index=[timedelta(), timedelta(minutes=3)])
    result = df.resample("1T").asfreq()
    expected = DataFrame(
        data=[1, np.nan, np.nan, 3],
        index=timedelta_range("0 day", periods=4, freq="1T"),
    )
    tm.assert_frame_equal(result, expected)


def test_resample_with_nat():
    # GH 13223
    index = pd.to_timedelta(["0s", pd.NaT, "2s"])
    result = DataFrame({"value": [2, 3, 5]}, index).resample("1s").mean()
    expected = DataFrame(
        {"value": [2.5, np.nan, 5.0]},
        index=timedelta_range("0 day", periods=3, freq="1S"),
    )
    tm.assert_frame_equal(result, expected)


def test_resample_as_freq_with_subperiod():
    # GH 13022
    index = timedelta_range("00:00:00", "00:10:00", freq="5T")
    df = DataFrame(data={"value": [1, 5, 10]}, index=index)
    result = df.resample("2T").asfreq()
    expected_data = {"value": [1, np.nan, np.nan, np.nan, np.nan, 10]}
    expected = DataFrame(
        data=expected_data, index=timedelta_range("00:00:00", "00:10:00", freq="2T")
    )
    tm.assert_frame_equal(result, expected)


def test_resample_with_timedeltas():

    expected = DataFrame({"A": np.arange(1480)})
    expected = expected.groupby(expected.index // 30).sum()
    expected.index = pd.timedelta_range("0 days", freq="30T", periods=50)

    df = DataFrame(
        {"A": np.arange(1480)}, index=pd.to_timedelta(np.arange(1480), unit="T")
    )
    result = df.resample("30T").sum()

    tm.assert_frame_equal(result, expected)

    s = df["A"]
    result = s.resample("30T").sum()
    tm.assert_series_equal(result, expected["A"])


def test_resample_single_period_timedelta():

    s = Series(list(range(5)), index=pd.timedelta_range("1 day", freq="s", periods=5))
    result = s.resample("2s").sum()
    expected = Series(
        [1, 5, 4], index=pd.timedelta_range("1 day", freq="2s", periods=3)
    )
    tm.assert_series_equal(result, expected)


def test_resample_timedelta_idempotency():

    # GH 12072
    index = pd.timedelta_range("0", periods=9, freq="10L")
    series = Series(range(9), index=index)
    result = series.resample("10L").mean()
    expected = series
    tm.assert_series_equal(result, expected)


def test_resample_base_with_timedeltaindex():

    # GH 10530
    rng = timedelta_range(start="0s", periods=25, freq="s")
    ts = Series(np.random.randn(len(rng)), index=rng)

    with_base = ts.resample("2s", base=5).mean()
    without_base = ts.resample("2s").mean()

    exp_without_base = timedelta_range(start="0s", end="25s", freq="2s")
    exp_with_base = timedelta_range(start="5s", end="29s", freq="2s")

    tm.assert_index_equal(without_base.index, exp_without_base)
    tm.assert_index_equal(with_base.index, exp_with_base)


def test_resample_categorical_data_with_timedeltaindex():
    # GH #12169
    df = DataFrame({"Group_obj": "A"}, index=pd.to_timedelta(list(range(20)), unit="s"))
    df["Group"] = df["Group_obj"].astype("category")
    result = df.resample("10s").agg(lambda x: (x.value_counts().index[0]))
    expected = DataFrame(
        {"Group_obj": ["A", "A"], "Group": ["A", "A"]},
        index=pd.TimedeltaIndex([0, 10], unit="s", freq="10s"),
    )
    expected = expected.reindex(["Group_obj", "Group"], axis=1)
    expected["Group"] = expected["Group_obj"]
    tm.assert_frame_equal(result, expected)


def test_resample_timedelta_values():
    # GH 13119
    # check that timedelta dtype is preserved when NaT values are
    # introduced by the resampling

    times = timedelta_range("1 day", "6 day", freq="4D")
    df = DataFrame({"time": times}, index=times)

    times2 = timedelta_range("1 day", "6 day", freq="2D")
    exp = Series(times2, index=times2, name="time")
    exp.iloc[1] = pd.NaT

    res = df.resample("2D").first()["time"]
    tm.assert_series_equal(res, exp)
    res = df["time"].resample("2D").first()
    tm.assert_series_equal(res, exp)


@pytest.mark.parametrize(
    "start, end, freq, resample_freq",
    [
        ("8H", "21h59min50s", "10S", "3H"),  # GH 30353 example
        ("3H", "22H", "1H", "5H"),
        ("527D", "5006D", "3D", "10D"),
        ("1D", "10D", "1D", "2D"),  # GH 13022 example
        # tests that worked before GH 33498:
        ("8H", "21h59min50s", "10S", "2H"),
        ("0H", "21h59min50s", "10S", "3H"),
        ("10D", "85D", "D", "2D"),
    ],
)
def test_resample_timedelta_edge_case(start, end, freq, resample_freq):
    # GH 33498
    # check that the timedelta bins does not contains an extra bin
    idx = pd.timedelta_range(start=start, end=end, freq=freq)
    s = pd.Series(np.arange(len(idx)), index=idx)
    result = s.resample(resample_freq).min()
    expected_index = pd.timedelta_range(freq=resample_freq, start=start, end=end)
    tm.assert_index_equal(result.index, expected_index)
    assert not np.isnan(result[-1])


@pytest.mark.parametrize(
    "start, end, freq",
    [
        ("1D", "10D", "2D"),
        ("2D", "30D", "3D"),
        ("2s", "50s", "5s"),
        # tests that worked before GH 33498:
        ("4D", "16D", "3D"),
        ("8D", "16D", "40s"),
    ],
)
def test_timedelta_range_freq_divide_end(start, end, freq):
    # GH 33498 only the cases where `(end % freq) == 0` used to fail

    def mock_timedelta_range(start=None, end=None, **kwargs):
        epoch = pd.Timestamp(0)
        if start is not None:
            start = epoch + pd.Timedelta(start)
        if end is not None:
            end = epoch + pd.Timedelta(end)
        result = pd.date_range(start=start, end=end, **kwargs) - epoch
        result.freq = freq
        return result

    res = pd.timedelta_range(start=start, end=end, freq=freq)
    exp = mock_timedelta_range(start=start, end=end, freq=freq)

    tm.assert_index_equal(res, exp)
