import numpy as np
import pytest

from pandas.compat.numpy import np_version_under1p17

from pandas import DataFrame, Series
import pandas._testing as tm
import pandas.core.common as com


class TestSample:
    @pytest.fixture(params=[Series, DataFrame])
    def obj(self, request):
        klass = request.param
        if klass is Series:
            arr = np.random.randn(10)
        else:
            arr = np.random.randn(10, 10)
        return klass(arr, dtype=None)

    @pytest.mark.parametrize("test", list(range(10)))
    def test_sample(self, test, obj):
        # Fixes issue: 2419
        # Check behavior of random_state argument
        # Check for stability when receives seed or random state -- run 10
        # times.

        seed = np.random.randint(0, 100)
        tm.assert_equal(
            obj.sample(n=4, random_state=seed), obj.sample(n=4, random_state=seed)
        )

        tm.assert_equal(
            obj.sample(frac=0.7, random_state=seed),
            obj.sample(frac=0.7, random_state=seed),
        )

        tm.assert_equal(
            obj.sample(n=4, random_state=np.random.RandomState(test)),
            obj.sample(n=4, random_state=np.random.RandomState(test)),
        )

        tm.assert_equal(
            obj.sample(frac=0.7, random_state=np.random.RandomState(test)),
            obj.sample(frac=0.7, random_state=np.random.RandomState(test)),
        )

        tm.assert_equal(
            obj.sample(frac=2, replace=True, random_state=np.random.RandomState(test)),
            obj.sample(frac=2, replace=True, random_state=np.random.RandomState(test)),
        )

        os1, os2 = [], []
        for _ in range(2):
            np.random.seed(test)
            os1.append(obj.sample(n=4))
            os2.append(obj.sample(frac=0.7))
        tm.assert_equal(*os1)
        tm.assert_equal(*os2)

    def test_sample_lengths(self, obj):
        # Check lengths are right
        assert len(obj.sample(n=4) == 4)
        assert len(obj.sample(frac=0.34) == 3)
        assert len(obj.sample(frac=0.36) == 4)

    def test_sample_invalid_random_state(self, obj):
        # Check for error when random_state argument invalid.
        with pytest.raises(ValueError):
            obj.sample(random_state="astring!")

    def test_sample_wont_accept_n_and_frac(self, obj):
        # Giving both frac and N throws error
        with pytest.raises(ValueError):
            obj.sample(n=3, frac=0.3)

    def test_sample_requires_positive_n_frac(self, obj):
        with pytest.raises(ValueError):
            obj.sample(n=-3)
        with pytest.raises(ValueError):
            obj.sample(frac=-0.3)

    def test_sample_requires_integer_n(self, obj):
        # Make sure float values of `n` give error
        with pytest.raises(ValueError):
            obj.sample(n=3.2)

    def test_sample_invalid_weight_lengths(self, obj):
        # Weight length must be right
        with pytest.raises(ValueError):
            obj.sample(n=3, weights=[0, 1])

        with pytest.raises(ValueError):
            bad_weights = [0.5] * 11
            obj.sample(n=3, weights=bad_weights)

        with pytest.raises(ValueError):
            bad_weight_series = Series([0, 0, 0.2])
            obj.sample(n=4, weights=bad_weight_series)

    def test_sample_negative_weights(self, obj):
        # Check won't accept negative weights
        with pytest.raises(ValueError):
            bad_weights = [-0.1] * 10
            obj.sample(n=3, weights=bad_weights)

    def test_sample_inf_weights(self, obj):
        # Check inf and -inf throw errors:

        with pytest.raises(ValueError):
            weights_with_inf = [0.1] * 10
            weights_with_inf[0] = np.inf
            obj.sample(n=3, weights=weights_with_inf)

        with pytest.raises(ValueError):
            weights_with_ninf = [0.1] * 10
            weights_with_ninf[0] = -np.inf
            obj.sample(n=3, weights=weights_with_ninf)

    def test_sample_zero_weights(self, obj):
        # All zeros raises errors

        zero_weights = [0] * 10
        with pytest.raises(ValueError):
            obj.sample(n=3, weights=zero_weights)

    def test_sample_missing_weights(self, obj):
        # All missing weights

        nan_weights = [np.nan] * 10
        with pytest.raises(ValueError):
            obj.sample(n=3, weights=nan_weights)

    def test_sample_none_weights(self, obj):
        # Check None are also replaced by zeros.
        weights_with_None = [None] * 10
        weights_with_None[5] = 0.5
        tm.assert_equal(
            obj.sample(n=1, axis=0, weights=weights_with_None), obj.iloc[5:6]
        )

    @pytest.mark.parametrize(
        "func_str,arg",
        [
            ("np.array", [2, 3, 1, 0]),
            pytest.param(
                "np.random.MT19937",
                3,
                marks=pytest.mark.skipif(np_version_under1p17, reason="NumPy<1.17"),
            ),
            pytest.param(
                "np.random.PCG64",
                11,
                marks=pytest.mark.skipif(np_version_under1p17, reason="NumPy<1.17"),
            ),
        ],
    )
    @pytest.mark.parametrize("klass", [Series, DataFrame])
    def test_sample_random_state(self, func_str, arg, klass):
        # GH#32503
        obj = DataFrame({"col1": range(10, 20), "col2": range(20, 30)})
        if klass is Series:
            obj = obj["col1"]
        result = obj.sample(n=3, random_state=eval(func_str)(arg))
        expected = obj.sample(n=3, random_state=com.random_state(eval(func_str)(arg)))
        tm.assert_equal(result, expected)

    @pytest.mark.parametrize("klass", [Series, DataFrame])
    def test_sample_upsampling_without_replacement(self, klass):
        # GH#27451

        obj = DataFrame({"A": list("abc")})
        if klass is Series:
            obj = obj["A"]

        msg = (
            "Replace has to be set to `True` when "
            "upsampling the population `frac` > 1."
        )
        with pytest.raises(ValueError, match=msg):
            obj.sample(frac=2, replace=False)


class TestSampleDataFrame:
    # Tests which are relevant only for DataFrame, so these are
    #  as fully parametrized as they can get.

    def test_sample(self):
        # GH#2419
        # additional specific object based tests

        # A few dataframe test with degenerate weights.
        easy_weight_list = [0] * 10
        easy_weight_list[5] = 1

        df = DataFrame(
            {
                "col1": range(10, 20),
                "col2": range(20, 30),
                "colString": ["a"] * 10,
                "easyweights": easy_weight_list,
            }
        )
        sample1 = df.sample(n=1, weights="easyweights")
        tm.assert_frame_equal(sample1, df.iloc[5:6])

        # Ensure proper error if string given as weight for Series or
        # DataFrame with axis = 1.
        ser = Series(range(10))
        with pytest.raises(ValueError):
            ser.sample(n=3, weights="weight_column")

        with pytest.raises(ValueError):
            df.sample(n=1, weights="weight_column", axis=1)

        # Check weighting key error
        with pytest.raises(
            KeyError, match="'String passed to weights not a valid column'"
        ):
            df.sample(n=3, weights="not_a_real_column_name")

        # Check that re-normalizes weights that don't sum to one.
        weights_less_than_1 = [0] * 10
        weights_less_than_1[0] = 0.5
        tm.assert_frame_equal(df.sample(n=1, weights=weights_less_than_1), df.iloc[:1])

        ###
        # Test axis argument
        ###

        # Test axis argument
        df = DataFrame({"col1": range(10), "col2": ["a"] * 10})
        second_column_weight = [0, 1]
        tm.assert_frame_equal(
            df.sample(n=1, axis=1, weights=second_column_weight), df[["col2"]]
        )

        # Different axis arg types
        tm.assert_frame_equal(
            df.sample(n=1, axis="columns", weights=second_column_weight), df[["col2"]]
        )

        weight = [0] * 10
        weight[5] = 0.5
        tm.assert_frame_equal(df.sample(n=1, axis="rows", weights=weight), df.iloc[5:6])
        tm.assert_frame_equal(
            df.sample(n=1, axis="index", weights=weight), df.iloc[5:6]
        )

        # Check out of range axis values
        with pytest.raises(ValueError):
            df.sample(n=1, axis=2)

        with pytest.raises(ValueError):
            df.sample(n=1, axis="not_a_name")

        with pytest.raises(ValueError):
            ser = Series(range(10))
            ser.sample(n=1, axis=1)

        # Test weight length compared to correct axis
        with pytest.raises(ValueError):
            df.sample(n=1, axis=1, weights=[0.5] * 10)

    def test_sample_axis1(self):
        # Check weights with axis = 1
        easy_weight_list = [0] * 3
        easy_weight_list[2] = 1

        df = DataFrame(
            {"col1": range(10, 20), "col2": range(20, 30), "colString": ["a"] * 10}
        )
        sample1 = df.sample(n=1, axis=1, weights=easy_weight_list)
        tm.assert_frame_equal(sample1, df[["colString"]])

        # Test default axes
        tm.assert_frame_equal(
            df.sample(n=3, random_state=42), df.sample(n=3, axis=0, random_state=42)
        )

    def test_sample_aligns_weights_with_frame(self):

        # Test that function aligns weights with frame
        df = DataFrame({"col1": [5, 6, 7], "col2": ["a", "b", "c"]}, index=[9, 5, 3])
        ser = Series([1, 0, 0], index=[3, 5, 9])
        tm.assert_frame_equal(df.loc[[3]], df.sample(1, weights=ser))

        # Weights have index values to be dropped because not in
        # sampled DataFrame
        ser2 = Series([0.001, 0, 10000], index=[3, 5, 10])
        tm.assert_frame_equal(df.loc[[3]], df.sample(1, weights=ser2))

        # Weights have empty values to be filed with zeros
        ser3 = Series([0.01, 0], index=[3, 5])
        tm.assert_frame_equal(df.loc[[3]], df.sample(1, weights=ser3))

        # No overlap in weight and sampled DataFrame indices
        ser4 = Series([1, 0], index=[1, 2])
        with pytest.raises(ValueError):
            df.sample(1, weights=ser4)

    def test_sample_is_copy(self):
        # GH#27357, GH#30784: ensure the result of sample is an actual copy and
        # doesn't track the parent dataframe / doesn't give SettingWithCopy warnings
        df = DataFrame(np.random.randn(10, 3), columns=["a", "b", "c"])
        df2 = df.sample(3)

        with tm.assert_produces_warning(None):
            df2["d"] = 1
