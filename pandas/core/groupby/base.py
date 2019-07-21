"""
Provide basic components for groupby. These defintiions
hold the whitelist of methods that are exposed on the
SeriesGroupBy and the DataFrameGroupBy objects.
"""
from pandas.core.dtypes.common import is_list_like, is_scalar


class GroupByMixin:
    """
    Provide the groupby facilities to the mixed object.
    """

    @staticmethod
    def _dispatch(name, *args, **kwargs):
        """
        Dispatch to apply.
        """

        def outer(self, *args, **kwargs):
            def f(x):
                x = self._shallow_copy(x, groupby=self._groupby)
                return getattr(x, name)(*args, **kwargs)

            return self._groupby.apply(f)

        outer.__name__ = name
        return outer

    def _gotitem(self, key, ndim, subset=None):
        """
        Sub-classes to define. Return a sliced object.

        Parameters
        ----------
        key : string / list of selections
        ndim : 1,2
            requested ndim of result
        subset : object, default None
            subset to act on
        """
        # create a new object to prevent aliasing
        if subset is None:
            subset = self.obj

        # we need to make a shallow copy of ourselves
        # with the same groupby
        kwargs = {attr: getattr(self, attr) for attr in self._attributes}

        # Try to select from a DataFrame, falling back to a Series
        try:
            groupby = self._groupby[key]
        except IndexError:
            groupby = self._groupby

        self = self.__class__(subset, groupby=groupby, parent=self, **kwargs)
        self._reset_cache()
        if subset.ndim == 2:
            if is_scalar(key) and key in subset or is_list_like(key):
                self._selection = key
        return self


# special case to prevent duplicate plots when catching exceptions when
# forwarding methods from NDFrames
plotting_methods = frozenset(["plot", "hist"])

common_apply_whitelist = (
    frozenset(
        [
            "quantile",
            "fillna",
            "mad",
            "take",
            "idxmax",
            "idxmin",
            "tshift",
            "skew",
            "corr",
            "cov",
            "diff",
        ]
    )
    | plotting_methods
)

series_apply_whitelist = (
    (
        common_apply_whitelist
        | {
            "nlargest",
            "nsmallest",
            "is_monotonic_increasing",
            "is_monotonic_decreasing",
        }
    )
) | frozenset(["dtype", "unique"])

dataframe_apply_whitelist = common_apply_whitelist | frozenset(["dtypes", "corrwith"])

# cythonized transformations or canned "agg+broadcast", which do not
# require postprocessing of the result by transform.
cythonized_kernels = frozenset(["cumprod", "cumsum", "shift", "cummin", "cummax"])

cython_cast_blacklist = frozenset(["rank", "count", "size", "idxmin", "idxmax"])

# List of aggregation/reduction functions.
# These map each series/column to a single value
reduction_kernels = frozenset(
    [
        "all",
        "any",
        "bfill",
        "count",
        "cov",
        "first",
        "idxmax",
        "idxmin",
        "last",
        "mad",
        "max",
        "mean",
        "median",
        "min",
        "ngroup",
        "nth",
        "nunique",
        "prod",
        "quantile",
        "sem",
        "size",
        "skew",
        "std",
        "sum",
        "var",
    ]
)

# List of transformation functions.
# These map each object to a like-indexed result object
transformation_kernels = frozenset(
    [
        "backfill",
        "corrwith",
        "cumcount",
        "cummax",
        "cummin",
        "cumprod",
        "cumsum",
        "diff",
        "ffill",
        "fillna",
        "pad",
        "pct_change",
        "rank",
        "shift",
        "tshift",
    ]
)

# Valid values  of `name` for `groupby.transform(name)`
# NOTE: do NOT edit this directly. New additions should be inserted
# into the appropriate list above.
transform_kernel_whitelist = reduction_kernels | transformation_kernels
