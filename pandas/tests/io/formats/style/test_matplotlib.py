import numpy as np
import pytest

from pandas import (
    DataFrame,
    IndexSlice,
    Series,
)

pytest.importorskip("matplotlib")
pytest.importorskip("jinja2")

from pandas.io.formats.style import Styler


@pytest.fixture
def df():
    return DataFrame([[1, 2], [2, 4]], columns=["A", "B"])


@pytest.fixture
def styler(df):
    return Styler(df, uuid_len=0)


@pytest.fixture
def df_blank():
    return DataFrame([[0, 0], [0, 0]], columns=["A", "B"], index=["X", "Y"])


@pytest.fixture
def styler_blank(df_blank):
    return Styler(df_blank, uuid_len=0)


def test_background_gradient(styler):
    for c_map in [None, "YlOrRd"]:
        result = styler.background_gradient(cmap=c_map)._compute().ctx
        assert all("#" in x[0][1] for x in result.values())
        assert result[(0, 0)] == result[(0, 1)]
        assert result[(1, 0)] == result[(1, 1)]


def test_background_gradient_color(styler):
    result = styler.background_gradient(subset=IndexSlice[1, "A"])._compute().ctx
    assert result[(1, 0)] == [("background-color", "#fff7fb"), ("color", "#000000")]


@pytest.mark.parametrize(
    "axis, expected",
    [
        (0, ["low", "low", "high", "high"]),
        (1, ["low", "high", "low", "high"]),
        (None, ["low", "mid", "mid", "high"]),
    ],
)
def test_background_gradient_axis(styler, axis, expected):
    bg_colors = {
        "low": [("background-color", "#f7fbff"), ("color", "#000000")],
        "mid": [("background-color", "#abd0e6"), ("color", "#000000")],
        "high": [("background-color", "#08306b"), ("color", "#f1f1f1")],
    }
    result = styler.background_gradient(cmap="Blues", axis=axis)._compute().ctx
    for i, cell in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
        assert result[cell] == bg_colors[expected[i]]


@pytest.mark.parametrize(
    "cmap, expected",
    [
        (
            "PuBu",
            {
                (4, 5): [("background-color", "#86b0d3"), ("color", "#000000")],
                (4, 6): [("background-color", "#83afd3"), ("color", "#f1f1f1")],
            },
        ),
        (
            "YlOrRd",
            {
                (4, 8): [("background-color", "#fd913e"), ("color", "#000000")],
                (4, 9): [("background-color", "#fd8f3d"), ("color", "#f1f1f1")],
            },
        ),
        (
            None,
            {
                (7, 0): [("background-color", "#48c16e"), ("color", "#f1f1f1")],
                (7, 1): [("background-color", "#4cc26c"), ("color", "#000000")],
            },
        ),
    ],
)
def test_text_color_threshold(cmap, expected):
    # GH 39888
    df = DataFrame(np.arange(100).reshape(10, 10))
    result = df.style.background_gradient(cmap=cmap, axis=None)._compute().ctx
    for k in expected.keys():
        assert result[k] == expected[k]


def test_background_gradient_vmin_vmax():
    # GH 12145
    df = DataFrame(range(5))
    ctx = df.style.background_gradient(vmin=1, vmax=3)._compute().ctx
    assert ctx[(0, 0)] == ctx[(1, 0)]
    assert ctx[(4, 0)] == ctx[(3, 0)]


def test_background_gradient_int64():
    # GH 28869
    df1 = Series(range(3)).to_frame()
    df2 = Series(range(3), dtype="Int64").to_frame()
    ctx1 = df1.style.background_gradient()._compute().ctx
    ctx2 = df2.style.background_gradient()._compute().ctx
    assert ctx2[(0, 0)] == ctx1[(0, 0)]
    assert ctx2[(1, 0)] == ctx1[(1, 0)]
    assert ctx2[(2, 0)] == ctx1[(2, 0)]


@pytest.mark.parametrize(
    "axis, gmap, expected",
    [
        (
            0,
            [1, 2],
            {
                (0, 0): [("background-color", "#fff7fb"), ("color", "#000000")],
                (1, 0): [("background-color", "#023858"), ("color", "#f1f1f1")],
                (0, 1): [("background-color", "#fff7fb"), ("color", "#000000")],
                (1, 1): [("background-color", "#023858"), ("color", "#f1f1f1")],
            },
        ),
        (
            1,
            [1, 2],
            {
                (0, 0): [("background-color", "#fff7fb"), ("color", "#000000")],
                (1, 0): [("background-color", "#fff7fb"), ("color", "#000000")],
                (0, 1): [("background-color", "#023858"), ("color", "#f1f1f1")],
                (1, 1): [("background-color", "#023858"), ("color", "#f1f1f1")],
            },
        ),
        (
            None,
            np.array([[2, 1], [1, 2]]),
            {
                (0, 0): [("background-color", "#023858"), ("color", "#f1f1f1")],
                (1, 0): [("background-color", "#fff7fb"), ("color", "#000000")],
                (0, 1): [("background-color", "#fff7fb"), ("color", "#000000")],
                (1, 1): [("background-color", "#023858"), ("color", "#f1f1f1")],
            },
        ),
    ],
)
def test_background_gradient_gmap_array(styler_blank, axis, gmap, expected):
    # tests when gmap is given as a sequence and converted to ndarray
    result = styler_blank.background_gradient(axis=axis, gmap=gmap)._compute().ctx
    assert result == expected


@pytest.mark.parametrize(
    "gmap, axis", [([1, 2, 3], 0), ([1, 2], 1), (np.array([[1, 2], [1, 2]]), None)]
)
def test_background_gradient_gmap_array_raises(gmap, axis):
    # test when gmap as converted ndarray is bad shape
    df = DataFrame([[0, 0, 0], [0, 0, 0]])
    msg = "supplied 'gmap' is not correct shape"
    with pytest.raises(ValueError, match=msg):
        df.style.background_gradient(gmap=gmap, axis=axis)._compute()


@pytest.mark.parametrize(
    "gmap",
    [
        DataFrame(  # reverse the columns
            [[2, 1], [1, 2]], columns=["B", "A"], index=["X", "Y"]
        ),
        DataFrame(  # reverse the index
            [[2, 1], [1, 2]], columns=["A", "B"], index=["Y", "X"]
        ),
        DataFrame(  # reverse the index and columns
            [[1, 2], [2, 1]], columns=["B", "A"], index=["Y", "X"]
        ),
        DataFrame(  # add unnecessary columns
            [[1, 2, 3], [2, 1, 3]], columns=["A", "B", "C"], index=["X", "Y"]
        ),
        DataFrame(  # add unnecessary index
            [[1, 2], [2, 1], [3, 3]], columns=["A", "B"], index=["X", "Y", "Z"]
        ),
    ],
)
@pytest.mark.parametrize(
    "subset, exp_gmap",  # exp_gmap is underlying map DataFrame should conform to
    [
        (None, [[1, 2], [2, 1]]),
        (["A"], [[1], [2]]),  # slice only column "A" in data and gmap
        (["B", "A"], [[2, 1], [1, 2]]),  # reverse the columns in data
        (IndexSlice["X", :], [[1, 2]]),  # slice only index "X" in data and gmap
        (IndexSlice[["Y", "X"], :], [[2, 1], [1, 2]]),  # reverse the index in data
    ],
)
def test_background_gradient_gmap_dataframe_align(styler_blank, gmap, subset, exp_gmap):
    # test gmap given as DataFrame that it aligns to the the data including subset
    expected = styler_blank.background_gradient(axis=None, gmap=exp_gmap, subset=subset)
    result = styler_blank.background_gradient(axis=None, gmap=gmap, subset=subset)
    assert expected._compute().ctx == result._compute().ctx


@pytest.mark.parametrize(
    "gmap, axis, exp_gmap",
    [
        (Series([2, 1], index=["Y", "X"]), 0, [[1, 1], [2, 2]]),  # revrse the index
        (Series([2, 1], index=["B", "A"]), 1, [[1, 2], [1, 2]]),  # revrse the cols
        (Series([1, 2, 3], index=["X", "Y", "Z"]), 0, [[1, 1], [2, 2]]),  # add idx
        (Series([1, 2, 3], index=["A", "B", "C"]), 1, [[1, 2], [1, 2]]),  # add col
    ],
)
def test_background_gradient_gmap_series_align(styler_blank, gmap, axis, exp_gmap):
    # test gmap given as Series that it aligns to the the data including subset
    expected = styler_blank.background_gradient(axis=None, gmap=exp_gmap)._compute()
    result = styler_blank.background_gradient(axis=axis, gmap=gmap)._compute()
    assert expected.ctx == result.ctx


@pytest.mark.parametrize(
    "gmap, axis",
    [
        (DataFrame([[1, 2], [2, 1]], columns=["A", "B"], index=["X", "Y"]), 1),
        (DataFrame([[1, 2], [2, 1]], columns=["A", "B"], index=["X", "Y"]), 0),
    ],
)
def test_background_gradient_gmap_wrong_dataframe(styler_blank, gmap, axis):
    # test giving a gmap in DataFrame but with wrong axis
    msg = "'gmap' is a DataFrame but underlying data for operations is a Series"
    with pytest.raises(ValueError, match=msg):
        styler_blank.background_gradient(gmap=gmap, axis=axis)._compute()


def test_background_gradient_gmap_wrong_series(styler_blank):
    # test giving a gmap in Series form but with wrong axis
    msg = "'gmap' is a Series but underlying data for operations is a DataFrame"
    gmap = Series([1, 2], index=["X", "Y"])
    with pytest.raises(ValueError, match=msg):
        styler_blank.background_gradient(gmap=gmap, axis=None)._compute()
