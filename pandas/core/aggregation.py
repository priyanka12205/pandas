"""
aggregation.py contains utility functions to handle multiple named and lambda
kwarg aggregations in groupby and DataFrame/Series aggregation
"""

from collections import defaultdict
from functools import partial
from typing import Any, DefaultDict, List, Optional, Sequence, Tuple, Union

from pandas._typing import Label

from pandas.core.dtypes.common import is_dict_like, is_list_like
from pandas.core.dtypes.generic import ABCDataFrame

from pandas.core.base import SpecificationError
import pandas.core.common as com
from pandas.core.indexes.api import Index


def reconstruct_func(
    func: Optional[Union[List, dict]], *args, **kwargs
) -> Tuple[bool, Any, Optional[List[Label]], Optional[List[int]]]:
    """
    This is the internal function to reconstruct func given if there is relabeling
    or not and also normalize the keyword to get new order of columns.

    If relabeling is True, will return relabeling, reconstructed func, column
    names, and the reconstructed order of columns.
    If relabeling is False, the columns and order will be None.

    Parameters
    ----------
    func: aggregated function
    **kwargs: dict, kwargs used in is_multi_agg_with_relabel and
        normalize_keyword_aggregation function for relabelling

    Returns
    -------
    relabelling: bool, if there is relabelling or not
    func: normalized and mangled func
    columns: list of column names
    order: list of columns indices

    Examples
    --------
    >>> reconstruct_func({"foo": ("col", "min")})
    True, {"col": ["min"]}, ("foo",), [0]

    >>> reconstruct_func("min")
    False, "min", None, None
    """
    relabeling = func is None and is_multi_agg_with_relabel(**kwargs)
    columns: Optional[List[str]] = None
    order: Optional[List[int]] = None

    if not relabeling:
        if isinstance(func, list) and len(func) > len(set(func)):

            # GH 28426 will raise error if duplicated function names are used and
            # there is no reassigned name
            raise SpecificationError(
                "Function names must be unique if there is no new column names"
                " assigned"
            )
        elif func is None:
            # nicer error message
            raise TypeError("Must provide 'func' or tuples of '(column, aggfunc).")

    if relabeling:
        func, columns, order = normalize_keyword_aggregation(kwargs)

    func = maybe_mangle_lambdas(func)

    return relabeling, func, columns, order


def is_multi_agg_with_relabel(**kwargs) -> bool:
    """
    Check whether kwargs passed to .agg look like multi-agg with relabeling.

    Parameters
    ----------
    **kwargs : dict

    Returns
    -------
    bool

    Examples
    --------
    >>> is_multi_agg_with_relabel(a='max')
    False
    >>> is_multi_agg_with_relabel(a_max=('a', 'max'),
    ...                            a_min=('a', 'min'))
    True
    >>> is_multi_agg_with_relabel()
    False
    """
    return all(isinstance(v, tuple) and len(v) == 2 for v in kwargs.values()) and (
        len(kwargs) > 0
    )


def normalize_keyword_aggregation(kwargs: dict) -> Tuple[dict, List[str], List[int]]:
    """
    Normalize user-provided "named aggregation" kwargs.
    Transforms from the new ``Mapping[str, NamedAgg]`` style kwargs
    to the old Dict[str, List[scalar]]].

    Parameters
    ----------
    kwargs : dict

    Returns
    -------
    aggspec : dict
        The transformed kwargs.
    columns : List[str]
        The user-provided keys.
    col_idx_order : List[int]
        List of columns indices.

    Examples
    --------
    >>> normalize_keyword_aggregation({'output': ('input', 'sum')})
    ({'input': ['sum']}, ('output',), [('input', 'sum')])
    """
    # Normalize the aggregation functions as Mapping[column, List[func]],
    # process normally, then fixup the names.
    # TODO: aggspec type: typing.Dict[str, List[AggScalar]]
    # May be hitting https://github.com/python/mypy/issues/5958
    # saying it doesn't have an attribute __name__
    aggspec: DefaultDict = defaultdict(list)
    order = []
    columns, pairs = list(zip(*kwargs.items()))

    for name, (column, aggfunc) in zip(columns, pairs):
        aggspec[column].append(aggfunc)
        order.append((column, com.get_callable_name(aggfunc) or aggfunc))

    # uniquify aggfunc name if duplicated in order list
    uniquified_order = _make_unique_kwarg_list(order)

    # GH 25719, due to aggspec will change the order of assigned columns in aggregation
    # uniquified_aggspec will store uniquified order list and will compare it with order
    # based on index
    aggspec_order = [
        (column, com.get_callable_name(aggfunc) or aggfunc)
        for column, aggfuncs in aggspec.items()
        for aggfunc in aggfuncs
    ]
    uniquified_aggspec = _make_unique_kwarg_list(aggspec_order)

    # get the new indice of columns by comparison
    col_idx_order = Index(uniquified_aggspec).get_indexer(uniquified_order)
    return aggspec, columns, col_idx_order


def _make_unique_kwarg_list(
    seq: Sequence[Tuple[Any, Any]]
) -> Sequence[Tuple[Any, Any]]:
    """Uniquify aggfunc name of the pairs in the order list

    Examples:
    --------
    >>> kwarg_list = [('a', '<lambda>'), ('a', '<lambda>'), ('b', '<lambda>')]
    >>> _make_unique_kwarg_list(kwarg_list)
    [('a', '<lambda>_0'), ('a', '<lambda>_1'), ('b', '<lambda>')]
    """
    return [
        (pair[0], "_".join([pair[1], str(seq[:i].count(pair))]))
        if seq.count(pair) > 1
        else pair
        for i, pair in enumerate(seq)
    ]


# TODO: Can't use, because mypy doesn't like us setting __name__
#   error: "partial[Any]" has no attribute "__name__"
# the type is:
#   typing.Sequence[Callable[..., ScalarResult]]
#     -> typing.Sequence[Callable[..., ScalarResult]]:


def _managle_lambda_list(aggfuncs: Sequence[Any]) -> Sequence[Any]:
    """
    Possibly mangle a list of aggfuncs.

    Parameters
    ----------
    aggfuncs : Sequence

    Returns
    -------
    mangled: list-like
        A new AggSpec sequence, where lambdas have been converted
        to have unique names.

    Notes
    -----
    If just one aggfunc is passed, the name will not be mangled.
    """
    if len(aggfuncs) <= 1:
        # don't mangle for .agg([lambda x: .])
        return aggfuncs
    i = 0
    mangled_aggfuncs = []
    for aggfunc in aggfuncs:
        if com.get_callable_name(aggfunc) == "<lambda>":
            aggfunc = partial(aggfunc)
            aggfunc.__name__ = f"<lambda_{i}>"
            i += 1
        mangled_aggfuncs.append(aggfunc)

    return mangled_aggfuncs


def maybe_mangle_lambdas(agg_spec: Any) -> Any:
    """
    Make new lambdas with unique names.

    Parameters
    ----------
    agg_spec : Any
        An argument to GroupBy.agg.
        Non-dict-like `agg_spec` are pass through as is.
        For dict-like `agg_spec` a new spec is returned
        with name-mangled lambdas.

    Returns
    -------
    mangled : Any
        Same type as the input.

    Examples
    --------
    >>> maybe_mangle_lambdas('sum')
    'sum'
    >>> maybe_mangle_lambdas([lambda: 1, lambda: 2])  # doctest: +SKIP
    [<function __main__.<lambda_0>,
     <function pandas...._make_lambda.<locals>.f(*args, **kwargs)>]
    """
    is_dict = is_dict_like(agg_spec)
    if not (is_dict or is_list_like(agg_spec)):
        return agg_spec
    mangled_aggspec = type(agg_spec)()  # dict or OrderdDict

    if is_dict:
        for key, aggfuncs in agg_spec.items():
            if is_list_like(aggfuncs) and not is_dict_like(aggfuncs):
                mangled_aggfuncs = _managle_lambda_list(aggfuncs)
            else:
                mangled_aggfuncs = aggfuncs

            mangled_aggspec[key] = mangled_aggfuncs
    else:
        mangled_aggspec = _managle_lambda_list(agg_spec)

    return mangled_aggspec


def _relabel_result(result, reordered_result, func, columns, order):
    """Internal function to reorder result if relabelling for dataframe.agg."""

    reordered_indexes = [
        pair[0] for pair in sorted(zip(columns, order), key=lambda t: t[1])
    ]
    idx = 0

    # The reason is self._aggregate outputs different type of result if
    # any column is only used once in aggregation
    mask = isinstance(result, ABCDataFrame) and result.isna().any().any()

    for col, fun in func.items():
        s = result[col][::-1].dropna() if mask else result[col]
        s.index = reordered_indexes[idx : idx + len(fun)]
        reordered_result[col] = s.reindex(columns)
        idx = idx + len(fun)
    return reordered_result
