import numpy as np

import pandas as pd
from pandas import DataFrame, Series
from pandas.core.indexes.timedeltas import timedelta_range
import pandas.util.testing as tm
from pandas.util.testing import assert_frame_equal, assert_series_equal


class TestTimedeltaIndex(object):
    def test_asfreq_bug(self):
        import datetime as dt
        df = DataFrame(data=[1, 3],
                       index=[dt.timedelta(), dt.timedelta(minutes=3)])
        result = df.resample('1T').asfreq()
        expected = DataFrame(data=[1, np.nan, np.nan, 3],
                             index=timedelta_range('0 day',
                                                   periods=4,
                                                   freq='1T'))
        assert_frame_equal(result, expected)

    def test_resample_with_nat(self):
        # GH 13223
        index = pd.to_timedelta(['0s', pd.NaT, '2s'])
        result = DataFrame({'value': [2, 3, 5]}, index).resample('1s').mean()
        expected = DataFrame({'value': [2.5, np.nan, 5.0]},
                             index=timedelta_range('0 day',
                                                   periods=3,
                                                   freq='1S'))
        assert_frame_equal(result, expected)

    def test_resample_as_freq_with_subperiod(self):
        # GH 13022
        index = timedelta_range('00:00:00', '00:10:00', freq='5T')
        df = DataFrame(data={'value': [1, 5, 10]}, index=index)
        result = df.resample('2T').asfreq()
        expected_data = {'value': [1, np.nan, np.nan, np.nan, np.nan, 10]}
        expected = DataFrame(data=expected_data,
                             index=timedelta_range('00:00:00',
                                                   '00:10:00', freq='2T'))
        tm.assert_frame_equal(result, expected)

    def test_resample_with_timedeltas(self):

        expected = DataFrame({'A': np.arange(1480)})
        expected = expected.groupby(expected.index // 30).sum()
        expected.index = pd.timedelta_range('0 days', freq='30T', periods=50)

        df = DataFrame({'A': np.arange(1480)}, index=pd.to_timedelta(
            np.arange(1480), unit='T'))
        result = df.resample('30T').sum()

        assert_frame_equal(result, expected)

        s = df['A']
        result = s.resample('30T').sum()
        assert_series_equal(result, expected['A'])

    def test_resample_single_period_timedelta(self):

        s = Series(list(range(5)), index=pd.timedelta_range(
            '1 day', freq='s', periods=5))
        result = s.resample('2s').sum()
        expected = Series([1, 5, 4], index=pd.timedelta_range(
            '1 day', freq='2s', periods=3))
        assert_series_equal(result, expected)

    def test_resample_timedelta_idempotency(self):

        # GH 12072
        index = pd.timedelta_range('0', periods=9, freq='10L')
        series = Series(range(9), index=index)
        result = series.resample('10L').mean()
        expected = series
        assert_series_equal(result, expected)

    def test_resample_base_with_timedeltaindex(self):

        # GH 10530
        rng = timedelta_range(start='0s', periods=25, freq='s')
        ts = Series(np.random.randn(len(rng)), index=rng)

        with_base = ts.resample('2s', base=5).mean()
        without_base = ts.resample('2s').mean()

        exp_without_base = timedelta_range(start='0s', end='25s', freq='2s')
        exp_with_base = timedelta_range(start='5s', end='29s', freq='2s')

        tm.assert_index_equal(without_base.index, exp_without_base)
        tm.assert_index_equal(with_base.index, exp_with_base)

    def test_resample_timedelta_values(self):
        # GH 13119
        # check that timedelta dtype is preserved when NaT values are
        # introduced by the resampling

        times = timedelta_range('1 day', '4 day', freq='4D')
        df = DataFrame({'time': times}, index=times)

        times2 = timedelta_range('1 day', '4 day', freq='2D')
        exp = Series(times2, index=times2, name='time')
        exp.iloc[1] = pd.NaT

        res = df.resample('2D').first()['time']
        tm.assert_series_equal(res, exp)
        res = df['time'].resample('2D').first()
        tm.assert_series_equal(res, exp)
