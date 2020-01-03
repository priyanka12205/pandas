from collections import defaultdict
from functools import partial
from typing import Any, Sequence

from pandas.core.dtypes.common import is_dict_like, is_list_like

from pandas.core.base import SpecificationError
import pandas.core.common as com
from pandas.core.indexes.api import Index


def reconstruct_func(func, *args, **kwargs):
    """
    This is the internal function to reconstruct func given if there is relabeling
    or not. And also normalize the keyword to get new order of columns;

    If relabeling is True, will return relabeling, reconstructed func, column
    names, and the reconstructed order of columns.
    If relabeling is False, the columns and order will be None.
    """
    relabeling = func is None and is_multi_agg_with_relabel(**kwargs)
    if relabeling:
        func, columns, order = normalize_keyword_aggregation(kwargs)

    elif isinstance(func, list) and len(func) > len(set(func)):

        # GH 28426 will raise error if duplicated function names are used and
        # there is no reassigned name
        raise SpecificationError(
            "Function names must be unique if there is no new column names assigned"
        )
    elif func is None:
        # nicer error message
        raise TypeError("Must provide 'func' or tuples of '(column, aggfunc).")

    func = maybe_mangle_lambdas(func)
    if not relabeling:
        columns = None
        order = None

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
    >>> _is_multi_agg_with_relabel(a='max')
    False
    >>> _is_multi_agg_with_relabel(a_max=('a', 'max'),
    ...                            a_min=('a', 'min'))
    True
    >>> _is_multi_agg_with_relabel()
    False
    """
    return all(isinstance(v, tuple) and len(v) == 2 for v in kwargs.values()) and (
        len(kwargs) > 0
    )


def normalize_keyword_aggregation(kwargs):
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
    >>> _normalize_keyword_aggregation({'output': ('input', 'sum')})
    ({'input': ['sum']}, ('output',), [('input', 'sum')])
    """
    # Normalize the aggregation functions as Mapping[column, List[func]],
    # process normally, then fixup the names.
    # TODO: aggspec type: typing.Dict[str, List[AggScalar]]
    # May be hitting https://github.com/python/mypy/issues/5958
    # saying it doesn't have an attribute __name__
    aggspec = defaultdict(list)
    order = []
    columns, pairs = list(zip(*kwargs.items()))

    for name, (column, aggfunc) in zip(columns, pairs):
        aggspec[column].append(aggfunc)
        order.append((column, com.get_callable_name(aggfunc) or aggfunc))

    # uniquify aggfunc name if duplicated in order list
    uniquified_order = _make_unique(order)

    # GH 25719, due to aggspec will change the order of assigned columns in aggregation
    # uniquified_aggspec will store uniquified order list and will compare it with order
    # based on index
    aggspec_order = [
        (column, com.get_callable_name(aggfunc) or aggfunc)
        for column, aggfuncs in aggspec.items()
        for aggfunc in aggfuncs
    ]
    uniquified_aggspec = _make_unique(aggspec_order)

    # get the new indice of columns by comparison
    col_idx_order = Index(uniquified_aggspec).get_indexer(uniquified_order)
    return aggspec, columns, col_idx_order


def _make_unique(seq):
    """Uniquify aggfunc name of the pairs in the order list

    Examples:
    --------
    >>> _make_unique([('a', '<lambda>'), ('a', '<lambda>'), ('b', '<lambda>')])
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
    >>> _maybe_mangle_lambdas('sum')
    'sum'

    >>> _maybe_mangle_lambdas([lambda: 1, lambda: 2])  # doctest: +SKIP
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
