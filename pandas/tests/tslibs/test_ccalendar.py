from datetime import date, datetime

import numpy as np
import pytest

from pandas._libs.tslibs import ccalendar


@pytest.mark.parametrize(
    "date_tuple,expected",
    [
        ((2001, 3, 1), 60),
        ((2004, 3, 1), 61),
        ((1907, 12, 31), 365),  # End-of-year, non-leap year.
        ((2004, 12, 31), 366),  # End-of-year, leap year.
    ],
)
def test_get_day_of_year_numeric(date_tuple, expected):
    assert ccalendar.get_day_of_year(*date_tuple) == expected


def test_get_day_of_year_dt():
    dt = datetime.fromordinal(1 + np.random.randint(365 * 4000))
    result = ccalendar.get_day_of_year(dt.year, dt.month, dt.day)

    expected = (dt - dt.replace(month=1, day=1)).days + 1
    assert result == expected


@pytest.mark.parametrize(
    "input_date_tuple, expected_iso_tuple",
    [
        [(2020, 1, 1), (2020, 1, 3)],
        [(2019, 12, 31), (2020, 1, 2)],
        [(2019, 12, 30), (2020, 1, 1)],
        [(2009, 12, 31), (2009, 53, 4)],
        [(2010, 1, 1), (2009, 53, 5)],
        [(2010, 1, 3), (2009, 53, 7)],
        [(2010, 1, 4), (2010, 1, 1)],
        [(2006, 1, 1), (2005, 52, 7)],
        [(2005, 12, 31), (2005, 52, 6)],
        [(2008, 12, 28), (2008, 52, 7)],
        [(2008, 12, 29), (2009, 1, 1)],
    ],
)
def test_dt_correct_iso_8601_year_week_and_day(input_date_tuple, expected_iso_tuple):
    assert (
        ccalendar.get_iso_calendar(*input_date_tuple)
        == date(*input_date_tuple).isocalendar()
    )
    assert ccalendar.get_iso_calendar(*input_date_tuple) == expected_iso_tuple
