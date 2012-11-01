import numpy as np

from pandas.core.frame import DataFrame
import pandas.core.nanops as nanops
from pandas.tseries.util import isleapyear

def pivot_annual(series, freq=None):
    """
    Group a series by years, taking leap years into account.

    The output has as many rows as distinct years in the original series,
    and as many columns as the length of a leap year in the units corresponding
    to the original frequency (366 for daily frequency, 366*24 for hourly...).
    The fist column of the output corresponds to Jan. 1st, 00:00:00,
    while the last column corresponds to Dec, 31st, 23:59:59.
    Entries corresponding to Feb. 29th are masked for non-leap years.

    For example, if the initial series has a daily frequency, the 59th column
    of the output always corresponds to Feb. 28th, the 61st column to Mar. 1st,
    and the 60th column is masked for non-leap years.
    With a hourly initial frequency, the (59*24)th column of the output always
    correspond to Feb. 28th 23:00, the (61*24)th column to Mar. 1st, 00:00, and
    the 24 columns between (59*24) and (61*24) are masked.

    If the original frequency is less than daily, the output is equivalent to
    ``series.convert('A', func=None)``.

    Parameters
    ----------
    series : TimeSeries
    freq : string or None, default None

    Returns
    -------
    annual : DataFrame
    """
    index = series.index
    year = index.year
    years = nanops.unique1d(year)

    if freq is not None:
        freq = freq.upper()
    else:
        freq = series.index.freq

    if freq == 'D':
        width = 366
        offset = index.dayofyear - 1

        # adjust for leap year
        offset[(-isleapyear(year)) & (offset >= 59)] += 1

        columns = range(1, 367)
        # todo: strings like 1/1, 1/25, etc.?
    elif freq in ('M', 'BM'):
        width = 12
        offset = index.month - 1
        columns = range(1, 13)
    else:
        raise NotImplementedError(freq)

    flat_index = (year - years.min()) * width + offset

    values = np.empty((len(years), width), dtype=series.dtype)

    if not np.issubdtype(series.dtype, np.integer):
        values.fill(np.nan)
    else:
        raise Exception('need to upcast')

    values.put(flat_index, series.values)

    return DataFrame(values, index=years, columns=columns)

def isleapyear(year):
    """
    Returns true if year is a leap year.

    Parameters
    ----------
    year : integer / sequence
        A given (list of) year(s).
    """
    year = np.asarray(year)
    return np.logical_or(year % 400 == 0,
                         np.logical_and(year % 4 == 0, year % 100 > 0))
