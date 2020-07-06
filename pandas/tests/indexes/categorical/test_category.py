import numpy as np
import pytest

from pandas._libs import index as libindex

import pandas as pd
from pandas import Categorical
import pandas._testing as tm
from pandas.core.indexes.api import CategoricalIndex, Index

from ..common import Base


class TestCategoricalIndex(Base):
    _holder = CategoricalIndex

    @pytest.fixture
    def index(self, request):
        return tm.makeCategoricalIndex(100)

    def create_index(self, categories=None, ordered=False):
        if categories is None:
            categories = list("cab")
        return CategoricalIndex(list("aabbca"), categories=categories, ordered=ordered)

    def test_can_hold_identifiers(self):
        idx = self.create_index(categories=list("abcd"))
        key = idx[0]
        assert idx._can_hold_identifiers_and_holds_name(key) is True

    @pytest.mark.parametrize(
        "func,op_name",
        [
            (lambda idx: idx - idx, "__sub__"),
            (lambda idx: idx + idx, "__add__"),
            (lambda idx: idx - ["a", "b"], "__sub__"),
            (lambda idx: idx + ["a", "b"], "__add__"),
            (lambda idx: ["a", "b"] - idx, "__rsub__"),
            (lambda idx: ["a", "b"] + idx, "__radd__"),
        ],
    )
    def test_disallow_addsub_ops(self, func, op_name):
        # GH 10039
        # set ops (+/-) raise TypeError
        idx = pd.Index(pd.Categorical(["a", "b"]))
        cat_or_list = "'(Categorical|list)' and '(Categorical|list)'"
        msg = "|".join(
            [
                f"cannot perform {op_name} with this index type: CategoricalIndex",
                "can only concatenate list",
                rf"unsupported operand type\(s\) for [\+-]: {cat_or_list}",
            ]
        )
        with pytest.raises(TypeError, match=msg):
            func(idx)

    def test_method_delegation(self):

        ci = CategoricalIndex(list("aabbca"), categories=list("cabdef"))
        result = ci.set_categories(list("cab"))
        tm.assert_index_equal(
            result, CategoricalIndex(list("aabbca"), categories=list("cab"))
        )

        ci = CategoricalIndex(list("aabbca"), categories=list("cab"))
        result = ci.rename_categories(list("efg"))
        tm.assert_index_equal(
            result, CategoricalIndex(list("ffggef"), categories=list("efg"))
        )

        # GH18862 (let rename_categories take callables)
        result = ci.rename_categories(lambda x: x.upper())
        tm.assert_index_equal(
            result, CategoricalIndex(list("AABBCA"), categories=list("CAB"))
        )

        ci = CategoricalIndex(list("aabbca"), categories=list("cab"))
        result = ci.add_categories(["d"])
        tm.assert_index_equal(
            result, CategoricalIndex(list("aabbca"), categories=list("cabd"))
        )

        ci = CategoricalIndex(list("aabbca"), categories=list("cab"))
        result = ci.remove_categories(["c"])
        tm.assert_index_equal(
            result,
            CategoricalIndex(list("aabb") + [np.nan] + ["a"], categories=list("ab")),
        )

        ci = CategoricalIndex(list("aabbca"), categories=list("cabdef"))
        result = ci.as_unordered()
        tm.assert_index_equal(result, ci)

        ci = CategoricalIndex(list("aabbca"), categories=list("cabdef"))
        result = ci.as_ordered()
        tm.assert_index_equal(
            result,
            CategoricalIndex(list("aabbca"), categories=list("cabdef"), ordered=True),
        )

        # invalid
        msg = "cannot use inplace with CategoricalIndex"
        with pytest.raises(ValueError, match=msg):
            ci.set_categories(list("cab"), inplace=True)

    def test_append(self):

        ci = self.create_index()
        categories = ci.categories

        # append cats with the same categories
        result = ci[:3].append(ci[3:])
        tm.assert_index_equal(result, ci, exact=True)

        foos = [ci[:1], ci[1:3], ci[3:]]
        result = foos[0].append(foos[1:])
        tm.assert_index_equal(result, ci, exact=True)

        # empty
        result = ci.append([])
        tm.assert_index_equal(result, ci, exact=True)

        # appending with different categories or reordered is not ok
        msg = "all inputs must be Index"
        with pytest.raises(TypeError, match=msg):
            ci.append(ci.values.set_categories(list("abcd")))
        with pytest.raises(TypeError, match=msg):
            ci.append(ci.values.reorder_categories(list("abc")))

        # with objects
        result = ci.append(Index(["c", "a"]))
        expected = CategoricalIndex(list("aabbcaca"), categories=categories)
        tm.assert_index_equal(result, expected, exact=True)

        # invalid objects
        msg = "cannot append a non-category item to a CategoricalIndex"
        with pytest.raises(TypeError, match=msg):
            ci.append(Index(["a", "d"]))

        # GH14298 - if base object is not categorical -> coerce to object
        result = Index(["c", "a"]).append(ci)
        expected = Index(list("caaabbca"))
        tm.assert_index_equal(result, expected, exact=True)

    def test_append_to_another(self):
        # hits Index._concat
        fst = Index(["a", "b"])
        snd = CategoricalIndex(["d", "e"])
        result = fst.append(snd)
        expected = Index(["a", "b", "d", "e"])
        tm.assert_index_equal(result, expected)

    def test_insert(self):

        ci = self.create_index()
        categories = ci.categories

        # test 0th element
        result = ci.insert(0, "a")
        expected = CategoricalIndex(list("aaabbca"), categories=categories)
        tm.assert_index_equal(result, expected, exact=True)

        # test Nth element that follows Python list behavior
        result = ci.insert(-1, "a")
        expected = CategoricalIndex(list("aabbcaa"), categories=categories)
        tm.assert_index_equal(result, expected, exact=True)

        # test empty
        result = CategoricalIndex(categories=categories).insert(0, "a")
        expected = CategoricalIndex(["a"], categories=categories)
        tm.assert_index_equal(result, expected, exact=True)

        # invalid
        msg = (
            "cannot insert an item into a CategoricalIndex that is not "
            "already an existing category"
        )
        with pytest.raises(TypeError, match=msg):
            ci.insert(0, "d")

        # GH 18295 (test missing)
        expected = CategoricalIndex(["a", np.nan, "a", "b", "c", "b"])
        for na in (np.nan, pd.NaT, None):
            result = CategoricalIndex(list("aabcb")).insert(1, na)
            tm.assert_index_equal(result, expected)

    def test_delete(self):

        ci = self.create_index()
        categories = ci.categories

        result = ci.delete(0)
        expected = CategoricalIndex(list("abbca"), categories=categories)
        tm.assert_index_equal(result, expected, exact=True)

        result = ci.delete(-1)
        expected = CategoricalIndex(list("aabbc"), categories=categories)
        tm.assert_index_equal(result, expected, exact=True)

        with tm.external_error_raised((IndexError, ValueError)):
            # Either depending on NumPy version
            ci.delete(10)

    @pytest.mark.parametrize(
        "data, non_lexsorted_data",
        [[[1, 2, 3], [9, 0, 1, 2, 3]], [list("abc"), list("fabcd")]],
    )
    def test_is_monotonic(self, data, non_lexsorted_data):
        c = CategoricalIndex(data)
        assert c.is_monotonic_increasing is True
        assert c.is_monotonic_decreasing is False

        c = CategoricalIndex(data, ordered=True)
        assert c.is_monotonic_increasing is True
        assert c.is_monotonic_decreasing is False

        c = CategoricalIndex(data, categories=reversed(data))
        assert c.is_monotonic_increasing is False
        assert c.is_monotonic_decreasing is True

        c = CategoricalIndex(data, categories=reversed(data), ordered=True)
        assert c.is_monotonic_increasing is False
        assert c.is_monotonic_decreasing is True

        # test when data is neither monotonic increasing nor decreasing
        reordered_data = [data[0], data[2], data[1]]
        c = CategoricalIndex(reordered_data, categories=reversed(data))
        assert c.is_monotonic_increasing is False
        assert c.is_monotonic_decreasing is False

        # non lexsorted categories
        categories = non_lexsorted_data

        c = CategoricalIndex(categories[:2], categories=categories)
        assert c.is_monotonic_increasing is True
        assert c.is_monotonic_decreasing is False

        c = CategoricalIndex(categories[1:3], categories=categories)
        assert c.is_monotonic_increasing is True
        assert c.is_monotonic_decreasing is False

    def test_has_duplicates(self):
        idx = CategoricalIndex([0, 0, 0], name="foo")
        assert idx.is_unique is False
        assert idx.has_duplicates is True

        idx = CategoricalIndex([0, 1], categories=[2, 3], name="foo")
        assert idx.is_unique is False
        assert idx.has_duplicates is True

        idx = CategoricalIndex([0, 1, 2, 3], categories=[1, 2, 3], name="foo")
        assert idx.is_unique is True
        assert idx.has_duplicates is False

    @pytest.mark.parametrize(
        "data, categories, expected",
        [
            (
                [1, 1, 1],
                [1, 2, 3],
                {
                    "first": np.array([False, True, True]),
                    "last": np.array([True, True, False]),
                    False: np.array([True, True, True]),
                },
            ),
            (
                [1, 1, 1],
                list("abc"),
                {
                    "first": np.array([False, True, True]),
                    "last": np.array([True, True, False]),
                    False: np.array([True, True, True]),
                },
            ),
            (
                [2, "a", "b"],
                list("abc"),
                {
                    "first": np.zeros(shape=(3), dtype=np.bool_),
                    "last": np.zeros(shape=(3), dtype=np.bool_),
                    False: np.zeros(shape=(3), dtype=np.bool_),
                },
            ),
            (
                list("abb"),
                list("abc"),
                {
                    "first": np.array([False, False, True]),
                    "last": np.array([False, True, False]),
                    False: np.array([False, True, True]),
                },
            ),
        ],
    )
    def test_drop_duplicates(self, data, categories, expected):

        idx = CategoricalIndex(data, categories=categories, name="foo")
        for keep, e in expected.items():
            tm.assert_numpy_array_equal(idx.duplicated(keep=keep), e)
            e = idx[~e]
            result = idx.drop_duplicates(keep=keep)
            tm.assert_index_equal(result, e)

    @pytest.mark.parametrize(
        "data, categories, expected_data, expected_categories",
        [
            ([1, 1, 1], [1, 2, 3], [1], [1]),
            ([1, 1, 1], list("abc"), [np.nan], []),
            ([1, 2, "a"], [1, 2, 3], [1, 2, np.nan], [1, 2]),
            ([2, "a", "b"], list("abc"), [np.nan, "a", "b"], ["a", "b"]),
        ],
    )
    def test_unique(self, data, categories, expected_data, expected_categories):

        idx = CategoricalIndex(data, categories=categories)
        expected = CategoricalIndex(expected_data, categories=expected_categories)
        tm.assert_index_equal(idx.unique(), expected)

    def test_repr_roundtrip(self):

        ci = CategoricalIndex(["a", "b"], categories=["a", "b"], ordered=True)
        str(ci)
        tm.assert_index_equal(eval(repr(ci)), ci, exact=True)

        # formatting
        str(ci)

        # long format
        # this is not reprable
        ci = CategoricalIndex(np.random.randint(0, 5, size=100))
        str(ci)

    def test_isin(self):

        ci = CategoricalIndex(list("aabca") + [np.nan], categories=["c", "a", "b"])
        tm.assert_numpy_array_equal(
            ci.isin(["c"]), np.array([False, False, False, True, False, False])
        )
        tm.assert_numpy_array_equal(
            ci.isin(["c", "a", "b"]), np.array([True] * 5 + [False])
        )
        tm.assert_numpy_array_equal(
            ci.isin(["c", "a", "b", np.nan]), np.array([True] * 6)
        )

        # mismatched categorical -> coerced to ndarray so doesn't matter
        result = ci.isin(ci.set_categories(list("abcdefghi")))
        expected = np.array([True] * 6)
        tm.assert_numpy_array_equal(result, expected)

        result = ci.isin(ci.set_categories(list("defghi")))
        expected = np.array([False] * 5 + [True])
        tm.assert_numpy_array_equal(result, expected)

    def test_identical(self):

        ci1 = CategoricalIndex(["a", "b"], categories=["a", "b"], ordered=True)
        ci2 = CategoricalIndex(["a", "b"], categories=["a", "b", "c"], ordered=True)
        assert ci1.identical(ci1)
        assert ci1.identical(ci1.copy())
        assert not ci1.identical(ci2)

    def test_ensure_copied_data(self, index):
        # gh-12309: Check the "copy" argument of each
        # Index.__new__ is honored.
        #
        # Must be tested separately from other indexes because
        # self.values is not an ndarray.
        # GH#29918 Index.base has been removed
        # FIXME: is this test still meaningful?
        _base = lambda ar: ar if getattr(ar, "base", None) is None else ar.base

        result = CategoricalIndex(index.values, copy=True)
        tm.assert_index_equal(index, result)
        assert _base(index.values) is not _base(result.values)

        result = CategoricalIndex(index.values, copy=False)
        assert _base(index.values) is _base(result.values)

    def test_equals_categorical(self):
        ci1 = CategoricalIndex(["a", "b"], categories=["a", "b"], ordered=True)
        ci2 = CategoricalIndex(["a", "b"], categories=["a", "b", "c"], ordered=True)

        assert ci1.equals(ci1)
        assert not ci1.equals(ci2)
        assert ci1.equals(ci1.astype(object))
        assert ci1.astype(object).equals(ci1)

        assert (ci1 == ci1).all()
        assert not (ci1 != ci1).all()
        assert not (ci1 > ci1).all()
        assert not (ci1 < ci1).all()
        assert (ci1 <= ci1).all()
        assert (ci1 >= ci1).all()

        assert not (ci1 == 1).all()
        assert (ci1 == Index(["a", "b"])).all()
        assert (ci1 == ci1.values).all()

        # invalid comparisons
        with pytest.raises(ValueError, match="Lengths must match"):
            ci1 == Index(["a", "b", "c"])

        msg = (
            "categorical index comparisons must have the same categories "
            "and ordered attributes"
            "|"
            "Categoricals can only be compared if 'categories' are the same. "
            "Categories are different lengths"
            "|"
            "Categoricals can only be compared if 'ordered' is the same"
        )
        with pytest.raises(TypeError, match=msg):
            ci1 == ci2
        with pytest.raises(TypeError, match=msg):
            ci1 == Categorical(ci1.values, ordered=False)
        with pytest.raises(TypeError, match=msg):
            ci1 == Categorical(ci1.values, categories=list("abc"))

        # tests
        # make sure that we are testing for category inclusion properly
        ci = CategoricalIndex(list("aabca"), categories=["c", "a", "b"])
        assert not ci.equals(list("aabca"))
        # Same categories, but different order
        # Unordered
        assert ci.equals(CategoricalIndex(list("aabca")))
        # Ordered
        assert not ci.equals(CategoricalIndex(list("aabca"), ordered=True))
        assert ci.equals(ci.copy())

        ci = CategoricalIndex(list("aabca") + [np.nan], categories=["c", "a", "b"])
        assert not ci.equals(list("aabca"))
        assert not ci.equals(CategoricalIndex(list("aabca")))
        assert ci.equals(ci.copy())

        ci = CategoricalIndex(list("aabca") + [np.nan], categories=["c", "a", "b"])
        assert not ci.equals(list("aabca") + [np.nan])
        assert ci.equals(CategoricalIndex(list("aabca") + [np.nan]))
        assert not ci.equals(CategoricalIndex(list("aabca") + [np.nan], ordered=True))
        assert ci.equals(ci.copy())

    def test_equals_categorical_unordered(self):
        # https://github.com/pandas-dev/pandas/issues/16603
        a = pd.CategoricalIndex(["A"], categories=["A", "B"])
        b = pd.CategoricalIndex(["A"], categories=["B", "A"])
        c = pd.CategoricalIndex(["C"], categories=["B", "A"])
        assert a.equals(b)
        assert not a.equals(c)
        assert not b.equals(c)

    def test_frame_repr(self):
        df = pd.DataFrame({"A": [1, 2, 3]}, index=pd.CategoricalIndex(["a", "b", "c"]))
        result = repr(df)
        expected = "   A\na  1\nb  2\nc  3"
        assert result == expected

    @pytest.mark.parametrize(
        "dtype, engine_type",
        [
            (np.int8, libindex.Int8Engine),
            (np.int16, libindex.Int16Engine),
            (np.int32, libindex.Int32Engine),
            (np.int64, libindex.Int64Engine),
        ],
    )
    def test_engine_type(self, dtype, engine_type):
        if dtype != np.int64:
            # num. of uniques required to push CategoricalIndex.codes to a
            # dtype (128 categories required for .codes dtype to be int16 etc.)
            num_uniques = {np.int8: 1, np.int16: 128, np.int32: 32768}[dtype]
            ci = pd.CategoricalIndex(range(num_uniques))
        else:
            # having 2**32 - 2**31 categories would be very memory-intensive,
            # so we cheat a bit with the dtype
            ci = pd.CategoricalIndex(range(32768))  # == 2**16 - 2**(16 - 1)
            ci.values._codes = ci.values._codes.astype("int64")
        assert np.issubdtype(ci.codes.dtype, dtype)
        assert isinstance(ci._engine, engine_type)

    def test_reindex_base(self):
        # See test_reindex.py
        pass

    def test_map_str(self):
        # See test_map.py
        pass
