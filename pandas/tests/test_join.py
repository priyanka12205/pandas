import numpy as np
import pytest

from pandas._libs import join as libjoin

from pandas import Index
import pandas._testing as tm


class TestIndexer:
    @pytest.mark.parametrize(
        "dtype", ["int32", "int64", "float32", "float64", "object"]
    )
    def test_outer_join_indexer(self, dtype):
        indexer = libjoin.outer_join_indexer

        left = np.arange(3, dtype=dtype)
        right = np.arange(2, 5, dtype=dtype)
        empty = np.array([], dtype=dtype)

        result, lindexer, rindexer = indexer(left, right)
        assert isinstance(result, np.ndarray)
        assert isinstance(lindexer, np.ndarray)
        assert isinstance(rindexer, np.ndarray)
        tm.assert_numpy_array_equal(result, np.arange(5, dtype=dtype))
        exp = np.array([0, 1, 2, -1, -1], dtype=np.int64)
        tm.assert_numpy_array_equal(lindexer, exp)
        exp = np.array([-1, -1, 0, 1, 2], dtype=np.int64)
        tm.assert_numpy_array_equal(rindexer, exp)

        result, lindexer, rindexer = indexer(empty, right)
        tm.assert_numpy_array_equal(result, right)
        exp = np.array([-1, -1, -1], dtype=np.int64)
        tm.assert_numpy_array_equal(lindexer, exp)
        exp = np.array([0, 1, 2], dtype=np.int64)
        tm.assert_numpy_array_equal(rindexer, exp)

        result, lindexer, rindexer = indexer(left, empty)
        tm.assert_numpy_array_equal(result, left)
        exp = np.array([0, 1, 2], dtype=np.int64)
        tm.assert_numpy_array_equal(lindexer, exp)
        exp = np.array([-1, -1, -1], dtype=np.int64)
        tm.assert_numpy_array_equal(rindexer, exp)


def test_left_join_indexer_unique():
    a = np.array([1, 2, 3, 4, 5], dtype=np.int64)
    b = np.array([2, 2, 3, 4, 4], dtype=np.int64)

    result = libjoin.left_join_indexer_unique(b, a)
    expected = np.array([1, 1, 2, 3, 3], dtype=np.int64)
    tm.assert_numpy_array_equal(result, expected)


def test_left_outer_join_bug():
    left = np.array(
        [
            0,
            1,
            0,
            1,
            1,
            2,
            3,
            1,
            0,
            2,
            1,
            2,
            0,
            1,
            1,
            2,
            3,
            2,
            3,
            2,
            1,
            1,
            3,
            0,
            3,
            2,
            3,
            0,
            0,
            2,
            3,
            2,
            0,
            3,
            1,
            3,
            0,
            1,
            3,
            0,
            0,
            1,
            0,
            3,
            1,
            0,
            1,
            0,
            1,
            1,
            0,
            2,
            2,
            2,
            2,
            2,
            0,
            3,
            1,
            2,
            0,
            0,
            3,
            1,
            3,
            2,
            2,
            0,
            1,
            3,
            0,
            2,
            3,
            2,
            3,
            3,
            2,
            3,
            3,
            1,
            3,
            2,
            0,
            0,
            3,
            1,
            1,
            1,
            0,
            2,
            3,
            3,
            1,
            2,
            0,
            3,
            1,
            2,
            0,
            2,
        ],
        dtype=np.int64,
    )

    right = np.array([3, 1], dtype=np.int64)
    max_groups = 4

    lidx, ridx = libjoin.left_outer_join(left, right, max_groups, sort=False)

    exp_lidx = np.arange(len(left), dtype=np.int64)
    exp_ridx = -np.ones(len(left), dtype=np.int64)

    exp_ridx[left == 1] = 1
    exp_ridx[left == 3] = 0

    tm.assert_numpy_array_equal(lidx, exp_lidx)
    tm.assert_numpy_array_equal(ridx, exp_ridx)


def test_inner_join_indexer():
    a = np.array([1, 2, 3, 4, 5], dtype=np.int64)
    b = np.array([0, 3, 5, 7, 9], dtype=np.int64)

    index, ares, bres = libjoin.inner_join_indexer(a, b)

    index_exp = np.array([3, 5], dtype=np.int64)
    tm.assert_almost_equal(index, index_exp)

    aexp = np.array([2, 4], dtype=np.int64)
    bexp = np.array([1, 2], dtype=np.int64)
    tm.assert_almost_equal(ares, aexp)
    tm.assert_almost_equal(bres, bexp)

    a = np.array([5], dtype=np.int64)
    b = np.array([5], dtype=np.int64)

    index, ares, bres = libjoin.inner_join_indexer(a, b)
    tm.assert_numpy_array_equal(index, np.array([5], dtype=np.int64))
    tm.assert_numpy_array_equal(ares, np.array([0], dtype=np.int64))
    tm.assert_numpy_array_equal(bres, np.array([0], dtype=np.int64))


def test_outer_join_indexer():
    a = np.array([1, 2, 3, 4, 5], dtype=np.int64)
    b = np.array([0, 3, 5, 7, 9], dtype=np.int64)

    index, ares, bres = libjoin.outer_join_indexer(a, b)

    index_exp = np.array([0, 1, 2, 3, 4, 5, 7, 9], dtype=np.int64)
    tm.assert_almost_equal(index, index_exp)

    aexp = np.array([-1, 0, 1, 2, 3, 4, -1, -1], dtype=np.int64)
    bexp = np.array([0, -1, -1, 1, -1, 2, 3, 4], dtype=np.int64)
    tm.assert_almost_equal(ares, aexp)
    tm.assert_almost_equal(bres, bexp)

    a = np.array([5], dtype=np.int64)
    b = np.array([5], dtype=np.int64)

    index, ares, bres = libjoin.outer_join_indexer(a, b)
    tm.assert_numpy_array_equal(index, np.array([5], dtype=np.int64))
    tm.assert_numpy_array_equal(ares, np.array([0], dtype=np.int64))
    tm.assert_numpy_array_equal(bres, np.array([0], dtype=np.int64))


def test_left_join_indexer():
    a = np.array([1, 2, 3, 4, 5], dtype=np.int64)
    b = np.array([0, 3, 5, 7, 9], dtype=np.int64)

    index, ares, bres = libjoin.left_join_indexer(a, b)

    tm.assert_almost_equal(index, a)

    aexp = np.array([0, 1, 2, 3, 4], dtype=np.int64)
    bexp = np.array([-1, -1, 1, -1, 2], dtype=np.int64)
    tm.assert_almost_equal(ares, aexp)
    tm.assert_almost_equal(bres, bexp)

    a = np.array([5], dtype=np.int64)
    b = np.array([5], dtype=np.int64)

    index, ares, bres = libjoin.left_join_indexer(a, b)
    tm.assert_numpy_array_equal(index, np.array([5], dtype=np.int64))
    tm.assert_numpy_array_equal(ares, np.array([0], dtype=np.int64))
    tm.assert_numpy_array_equal(bres, np.array([0], dtype=np.int64))


def test_left_join_indexer2():
    idx = Index([1, 1, 2, 5])
    idx2 = Index([1, 2, 5, 7, 9])

    res, lidx, ridx = libjoin.left_join_indexer(idx2.values, idx.values)

    exp_res = np.array([1, 1, 2, 5, 7, 9], dtype=np.int64)
    tm.assert_almost_equal(res, exp_res)

    exp_lidx = np.array([0, 0, 1, 2, 3, 4], dtype=np.int64)
    tm.assert_almost_equal(lidx, exp_lidx)

    exp_ridx = np.array([0, 1, 2, 3, -1, -1], dtype=np.int64)
    tm.assert_almost_equal(ridx, exp_ridx)


def test_outer_join_indexer2():
    idx = Index([1, 1, 2, 5])
    idx2 = Index([1, 2, 5, 7, 9])

    res, lidx, ridx = libjoin.outer_join_indexer(idx2.values, idx.values)

    exp_res = np.array([1, 1, 2, 5, 7, 9], dtype=np.int64)
    tm.assert_almost_equal(res, exp_res)

    exp_lidx = np.array([0, 0, 1, 2, 3, 4], dtype=np.int64)
    tm.assert_almost_equal(lidx, exp_lidx)

    exp_ridx = np.array([0, 1, 2, 3, -1, -1], dtype=np.int64)
    tm.assert_almost_equal(ridx, exp_ridx)


def test_inner_join_indexer2():
    idx = Index([1, 1, 2, 5])
    idx2 = Index([1, 2, 5, 7, 9])

    res, lidx, ridx = libjoin.inner_join_indexer(idx2.values, idx.values)

    exp_res = np.array([1, 1, 2, 5], dtype=np.int64)
    tm.assert_almost_equal(res, exp_res)

    exp_lidx = np.array([0, 0, 1, 2], dtype=np.int64)
    tm.assert_almost_equal(lidx, exp_lidx)

    exp_ridx = np.array([0, 1, 2, 3], dtype=np.int64)
    tm.assert_almost_equal(ridx, exp_ridx)
