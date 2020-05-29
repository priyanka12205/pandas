from pandas import Series
import pandas as pd
import numpy as np
from pandas.core.arrays.dates import DateArray
from pandas.core.dtypes.common import is_integer_dtype, is_extension_array_dtype
import pytest
import pandas.util.testing as tm

DATETIME_STRINGS = [
    "2001-01-01T12:00",
    "2002-02-03T13:56:03.172",
    "2007-07-13",
    "2006-01-13",
    "2010-08-13",
]
DATE_TEST_ARRAYS = [
        pd.array(np.arange(5, dtype=np.int64)),
        pd.array(pd.date_range("1970-01-01", periods=5, freq="D")),
        DateArray(np.arange(5, dtype=np.int64)),
    ]
VALID_CONVERSION_TYPES = ["object", "string", "i8", "datetime64[ns]"]
SECONDS_IN_A_DAY = 86400
NANO_SECONDS_IN_A_SECOND = 10 ** 9
NANO_SECONDS_IN_A_DAY = SECONDS_IN_A_DAY * NANO_SECONDS_IN_A_SECOND


@pytest.mark.parametrize("type", VALID_CONVERSION_TYPES)
def test_init_date_array_from_numpy(type: str):
    dt_range = pd.date_range("1970-01-01", periods=5, freq="D")

    date_range_as_type = dt_range.astype(type).to_numpy()
    if type == "i8":
        date_range_as_type //= NANO_SECONDS_IN_A_DAY
    arr = DateArray(date_range_as_type)
    tm.assert_numpy_array_equal(dt_range.date, arr.date)


@pytest.mark.parametrize(
    "arr",
    [
        pd.array(np.arange(5, dtype=np.int64)),
        pd.array(np.arange(5, dtype=np.object)),
        pd.date_range("1970-01-01", periods=5, freq="D").astype("object"),
        pd.array(np.array(DATETIME_STRINGS, dtype="datetime64")),
        # pd.array(np.array(DATETIME_STRINGS, dtype="object"), dtype="string"),
    ],
)
def test_date_from_pandas_array(arr):
    result = DateArray._from_sequence(arr)
    if is_integer_dtype(arr):
        arr *= NANO_SECONDS_IN_A_DAY
    tm.assert_numpy_array_equal(
        pd.array(arr.astype("datetime64[ns]")).date, result.date
    )


@pytest.fixture
def date_array():
    return DateArray._from_sequence(pd.array(np.arange(5, dtype=np.int64)))


def test_date_array_to_int(date_array):
    tm.assert_numpy_array_equal(date_array.astype("i8"), np.arange(5, dtype=np.int64))


def test_date_array_to_datetime64(date_array):
    tm.assert_numpy_array_equal(
        date_array.astype("datetime64[ns]").date,
        pd.date_range("1970-01-01", periods=5, freq="D").astype("datetime64[ns]").date,
    )


def test_date_array_to_str(date_array):
    object_dates = pd.array(
        np.array(["1970-01-0%d" % x for x in range(1, 6)]), dtype="string"
    )
    print(date_array.astype("string"))
    print(object_dates._ndarray)
    tm.assert_numpy_array_equal(date_array.astype("string"), object_dates._ndarray)


def test_series_has_extension_array():
    date_series = Series(DateArray(np.arange(5, dtype=np.int64)))
    assert is_extension_array_dtype(date_series.values)


@pytest.mark.parametrize(
    "arr",
    DATE_TEST_ARRAYS,
)
def test_other_type_to_date(arr):
    date_array = DateArray(np.arange(5, dtype=np.int64))
    other_arr_to_date = arr.astype("date")
    tm.assert_numpy_array_equal(date_array._data, other_arr_to_date._data)

@pytest.mark.parametrize(
    "arr",
    DATE_TEST_ARRAYS,
)
def test_other_type_to_date_series(arr):
    date_series = Series(DateArray(np.arange(5, dtype=np.int64)))
    other_series = Series(arr).astype("date")
    tm.assert_series_equal(date_series, other_series)

@pytest.fixture
def series():
    series = Series(["2019-01-01", "2020-12-11", "2020-10-11 12:11:12"])
    series.name = "strings"
    return series


@pytest.fixture
def df(series: Series):
    df = series.to_frame()
    df["strings"] = df["strings"].astype("string")
    return df


def test_dtype_name_display(df: pd.DataFrame, series: Series):
    df["dates"] = series.astype("datetime64").astype("date")
    assert df.dtypes[1] == "date"


def test_date_display_format(df: pd.DataFrame, series: Series):
    df["dates"] = series.astype("datetime64").astype("date")
    display = str(df["dates"])
    expected = (
        "0   2019-01-01\n"
        "1   2020-12-11\n"
        "2   2020-10-11\n"
        "Name: dates, dtype: date"
    )
    assert display == expected


def test_non_array_raises():
    with pytest.raises(ValueError, match="list"):
        DateArray([1, 2, 3])


def test_other_type_raises():
    with pytest.raises(ValueError, match="The dtype of 'values' is incorrect.*bool"):
        DateArray(np.array([1, 2, 3], dtype="bool"))


def test_copy():
    data = np.array([1, 2, 3], dtype="datetime64[D]")
    arr = DateArray(data, copy=False)
    assert arr._data is data

    arr = DateArray(data, copy=True)
    assert arr._data is not data


@pytest.mark.parametrize("dtype", [int, np.int32, np.int64, "uint32", "uint64"])
def test_astype_int(dtype):
    arr = DateArray._from_sequence([pd.Timestamp("2000"), pd.Timestamp("2001")])
    result = arr.astype(dtype)

    if np.dtype(dtype).kind == "u":
        expected_dtype = np.dtype("uint64")
    else:
        expected_dtype = np.dtype("int64")
    expected = arr.astype(expected_dtype)

    assert result.dtype == expected_dtype
    tm.assert_numpy_array_equal(result, expected)

if __name__ == '__main__':
    series = Series(["2019-01-01", "2020-12-11", "2020-10-11 12:11:12"])
    series.name = "strings"
    df = series.to_frame()
    df["strings"] = df["strings"].astype("string")
    test_dtype_name_display(df, series)