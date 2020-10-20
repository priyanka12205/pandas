from datetime import datetime

import numpy as np
import pytest

import pandas as pd
from pandas import (
    DataFrame,
    Index,
    Series,
    date_range,
)
import pandas._testing as tm


class TestDataFrameConcat:
    def test_concat_multiple_frames_dtypes(self):

        # GH#2759
        A = DataFrame(data=np.ones((10, 2)), columns=["foo", "bar"], dtype=np.float64)
        B = DataFrame(data=np.ones((10, 2)), dtype=np.float32)
        results = pd.concat((A, B), axis=1).dtypes
        expected = Series(
            [np.dtype("float64")] * 2 + [np.dtype("float32")] * 2,
            index=["foo", "bar", 0, 1],
        )
        tm.assert_series_equal(results, expected)

    def test_concat_tuple_keys(self):
        # GH#14438
        df1 = pd.DataFrame(np.ones((2, 2)), columns=list("AB"))
        df2 = pd.DataFrame(np.ones((3, 2)) * 2, columns=list("AB"))
        results = pd.concat((df1, df2), keys=[("bee", "bah"), ("bee", "boo")])
        expected = pd.DataFrame(
            {
                "A": {
                    ("bee", "bah", 0): 1.0,
                    ("bee", "bah", 1): 1.0,
                    ("bee", "boo", 0): 2.0,
                    ("bee", "boo", 1): 2.0,
                    ("bee", "boo", 2): 2.0,
                },
                "B": {
                    ("bee", "bah", 0): 1.0,
                    ("bee", "bah", 1): 1.0,
                    ("bee", "boo", 0): 2.0,
                    ("bee", "boo", 1): 2.0,
                    ("bee", "boo", 2): 2.0,
                },
            }
        )
        tm.assert_frame_equal(results, expected)

    def test_concat_named_keys(self):
        # GH#14252
        df = pd.DataFrame({"foo": [1, 2], "bar": [0.1, 0.2]})
        index = Index(["a", "b"], name="baz")
        concatted_named_from_keys = pd.concat([df, df], keys=index)
        expected_named = pd.DataFrame(
            {"foo": [1, 2, 1, 2], "bar": [0.1, 0.2, 0.1, 0.2]},
            index=pd.MultiIndex.from_product((["a", "b"], [0, 1]), names=["baz", None]),
        )
        tm.assert_frame_equal(concatted_named_from_keys, expected_named)

        index_no_name = Index(["a", "b"], name=None)
        concatted_named_from_names = pd.concat(
            [df, df], keys=index_no_name, names=["baz"]
        )
        tm.assert_frame_equal(concatted_named_from_names, expected_named)

        concatted_unnamed = pd.concat([df, df], keys=index_no_name)
        expected_unnamed = pd.DataFrame(
            {"foo": [1, 2, 1, 2], "bar": [0.1, 0.2, 0.1, 0.2]},
            index=pd.MultiIndex.from_product((["a", "b"], [0, 1]), names=[None, None]),
        )
        tm.assert_frame_equal(concatted_unnamed, expected_unnamed)

    def test_concat_axis_parameter(self):
        # GH#14369
        df1 = pd.DataFrame({"A": [0.1, 0.2]}, index=range(2))
        df2 = pd.DataFrame({"A": [0.3, 0.4]}, index=range(2))

        # Index/row/0 DataFrame
        expected_index = pd.DataFrame({"A": [0.1, 0.2, 0.3, 0.4]}, index=[0, 1, 0, 1])

        concatted_index = pd.concat([df1, df2], axis="index")
        tm.assert_frame_equal(concatted_index, expected_index)

        concatted_row = pd.concat([df1, df2], axis="rows")
        tm.assert_frame_equal(concatted_row, expected_index)

        concatted_0 = pd.concat([df1, df2], axis=0)
        tm.assert_frame_equal(concatted_0, expected_index)

        # Columns/1 DataFrame
        expected_columns = pd.DataFrame(
            [[0.1, 0.3], [0.2, 0.4]], index=[0, 1], columns=["A", "A"]
        )

        concatted_columns = pd.concat([df1, df2], axis="columns")
        tm.assert_frame_equal(concatted_columns, expected_columns)

        concatted_1 = pd.concat([df1, df2], axis=1)
        tm.assert_frame_equal(concatted_1, expected_columns)

        series1 = pd.Series([0.1, 0.2])
        series2 = pd.Series([0.3, 0.4])

        # Index/row/0 Series
        expected_index_series = pd.Series([0.1, 0.2, 0.3, 0.4], index=[0, 1, 0, 1])

        concatted_index_series = pd.concat([series1, series2], axis="index")
        tm.assert_series_equal(concatted_index_series, expected_index_series)

        concatted_row_series = pd.concat([series1, series2], axis="rows")
        tm.assert_series_equal(concatted_row_series, expected_index_series)

        concatted_0_series = pd.concat([series1, series2], axis=0)
        tm.assert_series_equal(concatted_0_series, expected_index_series)

        # Columns/1 Series
        expected_columns_series = pd.DataFrame(
            [[0.1, 0.3], [0.2, 0.4]], index=[0, 1], columns=[0, 1]
        )

        concatted_columns_series = pd.concat([series1, series2], axis="columns")
        tm.assert_frame_equal(concatted_columns_series, expected_columns_series)

        concatted_1_series = pd.concat([series1, series2], axis=1)
        tm.assert_frame_equal(concatted_1_series, expected_columns_series)

        # Testing ValueError
        with pytest.raises(ValueError, match="No axis named"):
            pd.concat([series1, series2], axis="something")

    def test_concat_numerical_names(self):
        # GH#15262, GH#12223
        df = pd.DataFrame(
            {"col": range(9)},
            dtype="int32",
            index=(
                pd.MultiIndex.from_product(
                    [["A0", "A1", "A2"], ["B0", "B1", "B2"]], names=[1, 2]
                )
            ),
        )
        result = pd.concat((df.iloc[:2, :], df.iloc[-2:, :]))
        expected = pd.DataFrame(
            {"col": [0, 1, 7, 8]},
            dtype="int32",
            index=pd.MultiIndex.from_tuples(
                [("A0", "B0"), ("A0", "B1"), ("A2", "B1"), ("A2", "B2")], names=[1, 2]
            ),
        )
        tm.assert_frame_equal(result, expected)

    def test_concat_astype_dup_col(self):
        # GH#23049
        df = pd.DataFrame([{"a": "b"}])
        df = pd.concat([df, df], axis=1)

        result = df.astype("category")
        expected = pd.DataFrame(
            np.array(["b", "b"]).reshape(1, 2), columns=["a", "a"]
        ).astype("category")
        tm.assert_frame_equal(result, expected)

    def test_concat_datetime_datetime64_frame(self):
        # GH#2624
        rows = []
        rows.append([datetime(2010, 1, 1), 1])
        rows.append([datetime(2010, 1, 2), "hi"])

        df2_obj = DataFrame.from_records(rows, columns=["date", "test"])

        ind = date_range(start="2000/1/1", freq="D", periods=10)
        df1 = DataFrame({"date": ind, "test": range(10)})

        # it works!
        pd.concat([df1, df2_obj])

    def test_concat_frame_axis0_extension_dtypes(self):
        # preserve extension dtype (through common_dtype mechanism)
        df1 = pd.DataFrame({"a": pd.array([1, 2, 3], dtype="Int64")})
        df2 = pd.DataFrame({"a": np.array([4, 5, 6])})

        result = pd.concat([df1, df2], ignore_index=True)
        expected = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6]}, dtype="Int64")
        tm.assert_frame_equal(result, expected)

        result = pd.concat([df2, df1], ignore_index=True)
        expected = pd.DataFrame({"a": [4, 5, 6, 1, 2, 3]}, dtype="Int64")
        tm.assert_frame_equal(result, expected)

    def test_concat_empty_and_non_empty_frame_regression(self):
        # GH 18178 regression test
        df1 = pd.DataFrame({"foo": [1]})
        df2 = pd.DataFrame({"foo": []})
        expected = pd.DataFrame({"foo": [1.0]})
        result = pd.concat([df1, df2])
        tm.assert_frame_equal(result, expected)
