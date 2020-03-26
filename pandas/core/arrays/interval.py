from operator import le, lt
import textwrap

import numpy as np

from pandas._config import get_option

from pandas._libs.interval import Interval, IntervalMixin, intervals_to_interval_bounds
from pandas.compat.numpy import function as nv
from pandas.util._decorators import Appender

from pandas.core.dtypes.cast import maybe_convert_platform
from pandas.core.dtypes.common import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_interval,
    is_interval_dtype,
    is_list_like,
    is_object_dtype,
    is_scalar,
    is_string_dtype,
    is_timedelta64_dtype,
    pandas_dtype,
)
from pandas.core.dtypes.dtypes import IntervalDtype
from pandas.core.dtypes.generic import (
    ABCDatetimeIndex,
    ABCExtensionArray,
    ABCIndexClass,
    ABCIntervalIndex,
    ABCPeriodIndex,
    ABCSeries,
)
from pandas.core.dtypes.missing import isna, notna

from pandas.core.algorithms import take, value_counts
from pandas.core.arrays.base import ExtensionArray, _extension_array_shared_docs
from pandas.core.arrays.categorical import Categorical
import pandas.core.common as com
from pandas.core.construction import array
from pandas.core.indexers import check_array_indexer
from pandas.core.indexes.base import ensure_index

_VALID_CLOSED = {"left", "right", "both", "neither"}
_interval_shared_docs = {}

_shared_docs_kwargs = dict(
    klass="IntervalArray", qualname="arrays.IntervalArray", name=""
)


_interval_shared_docs[
    "class"
] = """
%(summary)s

.. versionadded:: %(versionadded)s

Parameters
----------
data : array-like (1-dimensional)
    Array-like containing Interval objects from which to build the
    %(klass)s.
closed : {'left', 'right', 'both', 'neither'}, default 'right'
    Whether the intervals are closed on the left-side, right-side, both or
    neither.
dtype : dtype or None, default None
    If None, dtype will be inferred.

    .. versionadded:: 0.23.0
copy : bool, default False
    Copy the input data.
%(name)s\
verify_integrity : bool, default True
    Verify that the %(klass)s is valid.

Attributes
----------
left
right
closed
mid
length
is_empty
is_non_overlapping_monotonic
%(extra_attributes)s\

Methods
-------
from_arrays
from_tuples
from_breaks
contains
overlaps
set_closed
to_tuples
%(extra_methods)s\

See Also
--------
Index : The base pandas Index type.
Interval : A bounded slice-like interval; the elements of an %(klass)s.
interval_range : Function to create a fixed frequency IntervalIndex.
cut : Bin values into discrete Intervals.
qcut : Bin values into equal-sized Intervals based on rank or sample quantiles.

Notes
-----
See the `user guide
<https://pandas.pydata.org/pandas-docs/stable/user_guide/advanced.html#intervalindex>`_
for more.

%(examples)s\
"""


@Appender(
    _interval_shared_docs["class"]
    % dict(
        klass="IntervalArray",
        summary="Pandas array for interval data that are closed on the same side.",
        versionadded="0.24.0",
        name="",
        extra_attributes="",
        extra_methods="",
        examples=textwrap.dedent(
            """\
    Examples
    --------
    A new ``IntervalArray`` can be constructed directly from an array-like of
    ``Interval`` objects:

    >>> pd.arrays.IntervalArray([pd.Interval(0, 1), pd.Interval(1, 5)])
    <IntervalArray>
    [(0, 1], (1, 5]]
    Length: 2, closed: right, dtype: interval[int64]

    It may also be constructed using one of the constructor
    methods: :meth:`IntervalArray.from_arrays`,
    :meth:`IntervalArray.from_breaks`, and :meth:`IntervalArray.from_tuples`.
    """
        ),
    )
)
class IntervalArray(IntervalMixin, ExtensionArray):
    ndim = 1
    can_hold_na = True
    _na_value = _fill_value = np.nan

    def __new__(cls, data, closed=None, dtype=None, copy=False, verify_integrity=True):

        if isinstance(data, ABCSeries) and is_interval_dtype(data):
            data = data._values

        if isinstance(data, (cls, ABCIntervalIndex)):
            left = data.left
            right = data.right
            closed = closed or data.closed
        else:

            # don't allow scalars
            if is_scalar(data):
                msg = (
                    f"{cls.__name__}(...) must be called with a collection "
                    f"of some kind, {data} was passed"
                )
                raise TypeError(msg)

            # might need to convert empty or purely na data
            data = maybe_convert_platform_interval(data)
            left, right, infer_closed = intervals_to_interval_bounds(
                data, validate_closed=closed is None
            )
            closed = closed or infer_closed

        return cls._simple_new(
            left,
            right,
            closed,
            copy=copy,
            dtype=dtype,
            verify_integrity=verify_integrity,
        )

    @classmethod
    def _simple_new(
        cls, left, right, closed=None, copy=False, dtype=None, verify_integrity=True
    ):
        result = IntervalMixin.__new__(cls)

        closed = closed or "right"
        left = ensure_index(left, copy=copy)
        right = ensure_index(right, copy=copy)

        if dtype is not None:
            # GH 19262: dtype must be an IntervalDtype to override inferred
            dtype = pandas_dtype(dtype)
            if not is_interval_dtype(dtype):
                msg = f"dtype must be an IntervalDtype, got {dtype}"
                raise TypeError(msg)
            elif dtype.subtype is not None:
                left = left.astype(dtype.subtype)
                right = right.astype(dtype.subtype)

        # coerce dtypes to match if needed
        if is_float_dtype(left) and is_integer_dtype(right):
            right = right.astype(left.dtype)
        elif is_float_dtype(right) and is_integer_dtype(left):
            left = left.astype(right.dtype)

        if type(left) != type(right):
            msg = (
                f"must not have differing left [{type(left).__name__}] and "
                f"right [{type(right).__name__}] types"
            )
            raise ValueError(msg)
        elif is_categorical_dtype(left.dtype) or is_string_dtype(left.dtype):
            # GH 19016
            msg = (
                "category, object, and string subtypes are not supported "
                "for IntervalArray"
            )
            raise TypeError(msg)
        elif isinstance(left, ABCPeriodIndex):
            msg = "Period dtypes are not supported, use a PeriodIndex instead"
            raise ValueError(msg)
        elif isinstance(left, ABCDatetimeIndex) and str(left.tz) != str(right.tz):
            msg = (
                "left and right must have the same time zone, got "
                f"'{left.tz}' and '{right.tz}'"
            )
            raise ValueError(msg)

        result._left = left
        result._right = right
        result._closed = closed
        if verify_integrity:
            result._validate()
        return result

    @classmethod
    def _from_sequence(cls, scalars, dtype=None, copy=False):
        return cls(scalars, dtype=dtype, copy=copy)

    @classmethod
    def _from_factorized(cls, values, original):
        if len(values) == 0:
            # An empty array returns object-dtype here. We can't create
            # a new IA from an (empty) object-dtype array, so turn it into the
            # correct dtype.
            values = values.astype(original.dtype.subtype)
        return cls(values, closed=original.closed)

    _interval_shared_docs["from_breaks"] = textwrap.dedent(
        """
    Construct an %(klass)s from an array of splits.

    Parameters
    ----------
    breaks : array-like (1-dimensional)
        Left and right bounds for each interval.
    closed : {'left', 'right', 'both', 'neither'}, default 'right'
        Whether the intervals are closed on the left-side, right-side, both
        or neither.
    copy : bool, default False
        Copy the data.
    dtype : dtype or None, default None
        If None, dtype will be inferred.

        .. versionadded:: 0.23.0

    Returns
    -------
    %(klass)s

    See Also
    --------
    interval_range : Function to create a fixed frequency IntervalIndex.
    %(klass)s.from_arrays : Construct from a left and right array.
    %(klass)s.from_tuples : Construct from a sequence of tuples.

    %(examples)s\
    """
    )

    @classmethod
    @Appender(
        _interval_shared_docs["from_breaks"]
        % dict(
            klass="IntervalArray",
            examples=textwrap.dedent(
                """\
        Examples
        --------
        >>> pd.arrays.IntervalArray.from_breaks([0, 1, 2, 3])
        <IntervalArray>
        [(0, 1], (1, 2], (2, 3]]
        Length: 3, closed: right, dtype: interval[int64]
        """
            ),
        )
    )
    def from_breaks(cls, breaks, closed="right", copy=False, dtype=None):
        breaks = maybe_convert_platform_interval(breaks)

        return cls.from_arrays(breaks[:-1], breaks[1:], closed, copy=copy, dtype=dtype)

    _interval_shared_docs["from_arrays"] = textwrap.dedent(
        """
        Construct from two arrays defining the left and right bounds.

        Parameters
        ----------
        left : array-like (1-dimensional)
            Left bounds for each interval.
        right : array-like (1-dimensional)
            Right bounds for each interval.
        closed : {'left', 'right', 'both', 'neither'}, default 'right'
            Whether the intervals are closed on the left-side, right-side, both
            or neither.
        copy : bool, default False
            Copy the data.
        dtype : dtype, optional
            If None, dtype will be inferred.

            .. versionadded:: 0.23.0

        Returns
        -------
        %(klass)s

        Raises
        ------
        ValueError
            When a value is missing in only one of `left` or `right`.
            When a value in `left` is greater than the corresponding value
            in `right`.

        See Also
        --------
        interval_range : Function to create a fixed frequency IntervalIndex.
        %(klass)s.from_breaks : Construct an %(klass)s from an array of
            splits.
        %(klass)s.from_tuples : Construct an %(klass)s from an
            array-like of tuples.

        Notes
        -----
        Each element of `left` must be less than or equal to the `right`
        element at the same position. If an element is missing, it must be
        missing in both `left` and `right`. A TypeError is raised when
        using an unsupported type for `left` or `right`. At the moment,
        'category', 'object', and 'string' subtypes are not supported.

        %(examples)s\
        """
    )

    @classmethod
    @Appender(
        _interval_shared_docs["from_arrays"]
        % dict(
            klass="IntervalArray",
            examples=textwrap.dedent(
                """\
        >>> pd.arrays.IntervalArray.from_arrays([0, 1, 2], [1, 2, 3])
        <IntervalArray>
        [(0, 1], (1, 2], (2, 3]]
        Length: 3, closed: right, dtype: interval[int64]
        """
            ),
        )
    )
    def from_arrays(cls, left, right, closed="right", copy=False, dtype=None):
        left = maybe_convert_platform_interval(left)
        right = maybe_convert_platform_interval(right)

        return cls._simple_new(
            left, right, closed, copy=copy, dtype=dtype, verify_integrity=True
        )

    _interval_shared_docs["from_tuples"] = textwrap.dedent(
        """
    Construct an %(klass)s from an array-like of tuples.

    Parameters
    ----------
    data : array-like (1-dimensional)
        Array of tuples.
    closed : {'left', 'right', 'both', 'neither'}, default 'right'
        Whether the intervals are closed on the left-side, right-side, both
        or neither.
    copy : bool, default False
        By-default copy the data, this is compat only and ignored.
    dtype : dtype or None, default None
        If None, dtype will be inferred.

        .. versionadded:: 0.23.0

    Returns
    -------
    %(klass)s

    See Also
    --------
    interval_range : Function to create a fixed frequency IntervalIndex.
    %(klass)s.from_arrays : Construct an %(klass)s from a left and
                                right array.
    %(klass)s.from_breaks : Construct an %(klass)s from an array of
                                splits.

    %(examples)s\
    """
    )

    @classmethod
    @Appender(
        _interval_shared_docs["from_tuples"]
        % dict(
            klass="IntervalArray",
            examples=textwrap.dedent(
                """\
        Examples
        --------
        >>> pd.arrays.IntervalArray.from_tuples([(0, 1), (1, 2)])
        <IntervalArray>
        [(0, 1], (1, 2]]
        Length: 2, closed: right, dtype: interval[int64]
        """
            ),
        )
    )
    def from_tuples(cls, data, closed="right", copy=False, dtype=None):
        if len(data):
            left, right = [], []
        else:
            # ensure that empty data keeps input dtype
            left = right = data

        for d in data:
            if isna(d):
                lhs = rhs = np.nan
            else:
                name = cls.__name__
                try:
                    # need list of length 2 tuples, e.g. [(0, 1), (1, 2), ...]
                    lhs, rhs = d
                except ValueError as err:
                    msg = f"{name}.from_tuples requires tuples of length 2, got {d}"
                    raise ValueError(msg) from err
                except TypeError as err:
                    msg = f"{name}.from_tuples received an invalid item, {d}"
                    raise TypeError(msg) from err
            left.append(lhs)
            right.append(rhs)

        return cls.from_arrays(left, right, closed, copy=False, dtype=dtype)

    def _validate(self):
        """
        Verify that the IntervalArray is valid.

        Checks that

        * closed is valid
        * left and right match lengths
        * left and right have the same missing values
        * left is always below right
        """
        if self.closed not in _VALID_CLOSED:
            msg = f"invalid option for 'closed': {self.closed}"
            raise ValueError(msg)
        if len(self.left) != len(self.right):
            msg = "left and right must have the same length"
            raise ValueError(msg)
        left_mask = notna(self.left)
        right_mask = notna(self.right)
        if not (left_mask == right_mask).all():
            msg = (
                "missing values must be missing in the same "
                "location both left and right sides"
            )
            raise ValueError(msg)
        if not (self.left[left_mask] <= self.right[left_mask]).all():
            msg = "left side of interval must be <= right side"
            raise ValueError(msg)

    # ---------
    # Interface
    # ---------
    def __iter__(self):
        return iter(np.asarray(self))

    def __len__(self) -> int:
        return len(self.left)

    def __getitem__(self, value):
        value = check_array_indexer(self, value)
        left = self.left[value]
        right = self.right[value]

        # scalar
        if not isinstance(left, ABCIndexClass):
            if is_scalar(left) and isna(left):
                return self._fill_value
            if np.ndim(left) > 1:
                # GH#30588 multi-dimensional indexer disallowed
                raise ValueError("multi-dimensional indexing not allowed")
            return Interval(left, right, self.closed)

        return self._shallow_copy(left, right)

    def __setitem__(self, key, value):
        # na value: need special casing to set directly on numpy arrays
        needs_float_conversion = False
        if is_scalar(value) and isna(value):
            if is_integer_dtype(self.dtype.subtype):
                # can't set NaN on a numpy integer array
                needs_float_conversion = True
            elif is_datetime64_any_dtype(self.dtype.subtype):
                # need proper NaT to set directly on the numpy array
                value = np.datetime64("NaT")
            elif is_timedelta64_dtype(self.dtype.subtype):
                # need proper NaT to set directly on the numpy array
                value = np.timedelta64("NaT")
            value_left, value_right = value, value

        # scalar interval
        elif is_interval_dtype(value) or isinstance(value, Interval):
            self._check_closed_matches(value, name="value")
            value_left, value_right = value.left, value.right

        else:
            # list-like of intervals
            try:
                array = IntervalArray(value)
                value_left, value_right = array.left, array.right
            except TypeError as err:
                # wrong type: not interval or NA
                msg = f"'value' should be an interval type, got {type(value)} instead."
                raise TypeError(msg) from err

        key = check_array_indexer(self, key)
        # Need to ensure that left and right are updated atomically, so we're
        # forced to copy, update the copy, and swap in the new values.
        left = self.left.copy(deep=True)
        if needs_float_conversion:
            left = left.astype("float")
        left.values[key] = value_left
        self._left = left

        right = self.right.copy(deep=True)
        if needs_float_conversion:
            right = right.astype("float")
        right.values[key] = value_right
        self._right = right

    def __eq__(self, other):
        # ensure pandas array for list-like and eliminate non-interval scalars
        if is_list_like(other):
            if len(self) != len(other):
                raise ValueError("Lengths must match to compare")
            other = array(other)
        elif not isinstance(other, Interval):
            # non-interval scalar -> no matches
            return np.zeros(len(self), dtype=bool)

        # determine the dtype of the elements we want to compare
        if isinstance(other, Interval):
            other_dtype = "interval"
        elif not is_categorical_dtype(other):
            other_dtype = other.dtype
        else:
            # for categorical defer to categories for dtype
            other_dtype = other.categories.dtype

            # extract intervals if we have interval categories with matching closed
            if is_interval_dtype(other_dtype):
                if self.closed != other.categories.closed:
                    return np.zeros(len(self), dtype=bool)
                other = other.categories.take(other.codes)

        # interval-like -> need same closed and matching endpoints
        if is_interval_dtype(other_dtype):
            if self.closed != other.closed:
                return np.zeros(len(self), dtype=bool)
            return (self.left == other.left) & (self.right == other.right)

        # non-interval/non-object dtype -> no matches
        if not is_object_dtype(other_dtype):
            return np.zeros(len(self), dtype=bool)

        # object dtype -> iteratively check for intervals
        result = np.zeros(len(self), dtype=bool)
        for i, obj in enumerate(other):
            # need object to be an Interval with same closed and endpoints
            if (
                isinstance(obj, Interval)
                and self.closed == obj.closed
                and self.left[i] == obj.left
                and self.right[i] == obj.right
            ):
                result[i] = True

        return result

    def __ne__(self, other):
        return ~self.__eq__(other)

    def fillna(self, value=None, method=None, limit=None):
        """
        Fill NA/NaN values using the specified method.

        Parameters
        ----------
        value : scalar, dict, Series
            If a scalar value is passed it is used to fill all missing values.
            Alternatively, a Series or dict can be used to fill in different
            values for each index. The value should not be a list. The
            value(s) passed should be either Interval objects or NA/NaN.
        method : {'backfill', 'bfill', 'pad', 'ffill', None}, default None
            (Not implemented yet for IntervalArray)
            Method to use for filling holes in reindexed Series
        limit : int, default None
            (Not implemented yet for IntervalArray)
            If method is specified, this is the maximum number of consecutive
            NaN values to forward/backward fill. In other words, if there is
            a gap with more than this number of consecutive NaNs, it will only
            be partially filled. If method is not specified, this is the
            maximum number of entries along the entire axis where NaNs will be
            filled.

        Returns
        -------
        filled : IntervalArray with NA/NaN filled
        """
        if method is not None:
            raise TypeError("Filling by method is not supported for IntervalArray.")
        if limit is not None:
            raise TypeError("limit is not supported for IntervalArray.")

        if not isinstance(value, Interval):
            msg = (
                "'IntervalArray.fillna' only supports filling with a "
                f"scalar 'pandas.Interval'. Got a '{type(value).__name__}' instead."
            )
            raise TypeError(msg)

        value = getattr(value, "_values", value)
        self._check_closed_matches(value, name="value")

        left = self.left.fillna(value=value.left)
        right = self.right.fillna(value=value.right)
        return self._shallow_copy(left, right)

    @property
    def dtype(self):
        return IntervalDtype(self.left.dtype)

    def astype(self, dtype, copy=True):
        """
        Cast to an ExtensionArray or NumPy array with dtype 'dtype'.

        Parameters
        ----------
        dtype : str or dtype
            Typecode or data-type to which the array is cast.

        copy : bool, default True
            Whether to copy the data, even if not necessary. If False,
            a copy is made only if the old dtype does not match the
            new dtype.

        Returns
        -------
        array : ExtensionArray or ndarray
            ExtensionArray or NumPy ndarray with 'dtype' for its dtype.
        """
        dtype = pandas_dtype(dtype)
        if is_interval_dtype(dtype):
            if dtype == self.dtype:
                return self.copy() if copy else self

            # need to cast to different subtype
            try:
                new_left = self.left.astype(dtype.subtype)
                new_right = self.right.astype(dtype.subtype)
            except TypeError as err:
                msg = (
                    f"Cannot convert {self.dtype} to {dtype}; subtypes are incompatible"
                )
                raise TypeError(msg) from err
            return self._shallow_copy(new_left, new_right)
        elif is_categorical_dtype(dtype):
            return Categorical(np.asarray(self))
        # TODO: This try/except will be repeated.
        try:
            return np.asarray(self).astype(dtype, copy=copy)
        except (TypeError, ValueError) as err:
            msg = f"Cannot cast {type(self).__name__} to dtype {dtype}"
            raise TypeError(msg) from err

    @classmethod
    def _concat_same_type(cls, to_concat):
        """
        Concatenate multiple IntervalArray

        Parameters
        ----------
        to_concat : sequence of IntervalArray

        Returns
        -------
        IntervalArray
        """
        closed = {interval.closed for interval in to_concat}
        if len(closed) != 1:
            raise ValueError("Intervals must all be closed on the same side.")
        closed = closed.pop()

        left = np.concatenate([interval.left for interval in to_concat])
        right = np.concatenate([interval.right for interval in to_concat])
        return cls._simple_new(left, right, closed=closed, copy=False)

    def _shallow_copy(self, left, right):
        """
        Return a new IntervalArray with the replacement attributes

        Parameters
        ----------
        left : Index
            Values to be used for the left-side of the intervals.
        right : Index
            Values to be used for the right-side of the intervals.
        """
        return self._simple_new(left, right, closed=self.closed, verify_integrity=False)

    def copy(self):
        """
        Return a copy of the array.

        Returns
        -------
        IntervalArray
        """
        left = self.left.copy(deep=True)
        right = self.right.copy(deep=True)
        closed = self.closed
        # TODO: Could skip verify_integrity here.
        return type(self).from_arrays(left, right, closed=closed)

    def isna(self):
        return isna(self.left)

    @property
    def nbytes(self) -> int:
        return self.left.nbytes + self.right.nbytes

    @property
    def size(self) -> int:
        # Avoid materializing self.values
        return self.left.size

    def shift(self, periods: int = 1, fill_value: object = None) -> ABCExtensionArray:
        if not len(self) or periods == 0:
            return self.copy()

        if isna(fill_value):
            fill_value = self.dtype.na_value

        # ExtensionArray.shift doesn't work for two reasons
        # 1. IntervalArray.dtype.na_value may not be correct for the dtype.
        # 2. IntervalArray._from_sequence only accepts NaN for missing values,
        #    not other values like NaT

        empty_len = min(abs(periods), len(self))
        if isna(fill_value):
            fill_value = self.left._na_value
            empty = IntervalArray.from_breaks([fill_value] * (empty_len + 1))
        else:
            empty = self._from_sequence([fill_value] * empty_len)

        if periods > 0:
            a = empty
            b = self[:-periods]
        else:
            a = self[abs(periods) :]
            b = empty
        return self._concat_same_type([a, b])

    def take(self, indices, allow_fill=False, fill_value=None, axis=None, **kwargs):
        """
        Take elements from the IntervalArray.

        Parameters
        ----------
        indices : sequence of integers
            Indices to be taken.

        allow_fill : bool, default False
            How to handle negative values in `indices`.

            * False: negative values in `indices` indicate positional indices
              from the right (the default). This is similar to
              :func:`numpy.take`.

            * True: negative values in `indices` indicate
              missing values. These values are set to `fill_value`. Any other
              other negative values raise a ``ValueError``.

        fill_value : Interval or NA, optional
            Fill value to use for NA-indices when `allow_fill` is True.
            This may be ``None``, in which case the default NA value for
            the type, ``self.dtype.na_value``, is used.

            For many ExtensionArrays, there will be two representations of
            `fill_value`: a user-facing "boxed" scalar, and a low-level
            physical NA value. `fill_value` should be the user-facing version,
            and the implementation should handle translating that to the
            physical version for processing the take if necessary.

        axis : any, default None
            Present for compat with IntervalIndex; does nothing.

        Returns
        -------
        IntervalArray

        Raises
        ------
        IndexError
            When the indices are out of bounds for the array.
        ValueError
            When `indices` contains negative values other than ``-1``
            and `allow_fill` is True.
        """
        nv.validate_take(tuple(), kwargs)

        fill_left = fill_right = fill_value
        if allow_fill:
            if fill_value is None:
                fill_left = fill_right = self.left._na_value
            elif is_interval(fill_value):
                self._check_closed_matches(fill_value, name="fill_value")
                fill_left, fill_right = fill_value.left, fill_value.right
            elif not is_scalar(fill_value) and notna(fill_value):
                msg = (
                    "'IntervalArray.fillna' only supports filling with a "
                    "'scalar pandas.Interval or NA'. "
                    f"Got a '{type(fill_value).__name__}' instead."
                )
                raise ValueError(msg)

        left_take = take(
            self.left, indices, allow_fill=allow_fill, fill_value=fill_left
        )
        right_take = take(
            self.right, indices, allow_fill=allow_fill, fill_value=fill_right
        )

        return self._shallow_copy(left_take, right_take)

    def value_counts(self, dropna=True):
        """
        Returns a Series containing counts of each interval.

        Parameters
        ----------
        dropna : bool, default True
            Don't include counts of NaN.

        Returns
        -------
        counts : Series

        See Also
        --------
        Series.value_counts
        """
        # TODO: implement this is a non-naive way!
        return value_counts(np.asarray(self), dropna=dropna)

    # Formatting

    def _format_data(self):

        # TODO: integrate with categorical and make generic
        # name argument is unused here; just for compat with base / categorical
        n = len(self)
        max_seq_items = min((get_option("display.max_seq_items") or n) // 10, 10)

        formatter = str

        if n == 0:
            summary = "[]"
        elif n == 1:
            first = formatter(self[0])
            summary = f"[{first}]"
        elif n == 2:
            first = formatter(self[0])
            last = formatter(self[-1])
            summary = f"[{first}, {last}]"
        else:

            if n > max_seq_items:
                n = min(max_seq_items // 2, 10)
                head = [formatter(x) for x in self[:n]]
                tail = [formatter(x) for x in self[-n:]]
                head_str = ", ".join(head)
                tail_str = ", ".join(tail)
                summary = f"[{head_str} ... {tail_str}]"
            else:
                tail = [formatter(x) for x in self]
                tail_str = ", ".join(tail)
                summary = f"[{tail_str}]"

        return summary

    def __repr__(self) -> str:
        # the short repr has no trailing newline, while the truncated
        # repr does. So we include a newline in our template, and strip
        # any trailing newlines from format_object_summary
        data = self._format_data()
        class_name = f"<{type(self).__name__}>\n"

        template = (
            f"{class_name}"
            f"{data}\n"
            f"Length: {len(self)}, closed: {self.closed}, dtype: {self.dtype}"
        )
        return template

    def _format_space(self):
        space = " " * (len(type(self).__name__) + 1)
        return f"\n{space}"

    @property
    def left(self):
        """
        Return the left endpoints of each Interval in the IntervalArray as
        an Index.
        """
        return self._left

    @property
    def right(self):
        """
        Return the right endpoints of each Interval in the IntervalArray as
        an Index.
        """
        return self._right

    @property
    def closed(self):
        """
        Whether the intervals are closed on the left-side, right-side, both or
        neither.
        """
        return self._closed

    _interval_shared_docs["set_closed"] = textwrap.dedent(
        """
        Return an %(klass)s identical to the current one, but closed on the
        specified side.

        .. versionadded:: 0.24.0

        Parameters
        ----------
        closed : {'left', 'right', 'both', 'neither'}
            Whether the intervals are closed on the left-side, right-side, both
            or neither.

        Returns
        -------
        new_index : %(klass)s

        %(examples)s\
        """
    )

    @Appender(
        _interval_shared_docs["set_closed"]
        % dict(
            klass="IntervalArray",
            examples=textwrap.dedent(
                """\
        Examples
        --------
        >>> index = pd.arrays.IntervalArray.from_breaks(range(4))
        >>> index
        <IntervalArray>
        [(0, 1], (1, 2], (2, 3]]
        Length: 3, closed: right, dtype: interval[int64]
        >>> index.set_closed('both')
        <IntervalArray>
        [[0, 1], [1, 2], [2, 3]]
        Length: 3, closed: both, dtype: interval[int64]
        """
            ),
        )
    )
    def set_closed(self, closed):
        if closed not in _VALID_CLOSED:
            msg = f"invalid option for 'closed': {closed}"
            raise ValueError(msg)

        return type(self)._simple_new(
            left=self.left, right=self.right, closed=closed, verify_integrity=False
        )

    @property
    def length(self):
        """
        Return an Index with entries denoting the length of each Interval in
        the IntervalArray.
        """
        try:
            return self.right - self.left
        except TypeError as err:
            # length not defined for some types, e.g. string
            msg = (
                "IntervalArray contains Intervals without defined length, "
                "e.g. Intervals with string endpoints"
            )
            raise TypeError(msg) from err

    @property
    def mid(self):
        """
        Return the midpoint of each Interval in the IntervalArray as an Index.
        """
        try:
            return 0.5 * (self.left + self.right)
        except TypeError:
            # datetime safe version
            return self.left + 0.5 * self.length

    _interval_shared_docs[
        "is_non_overlapping_monotonic"
    ] = """
        Return True if the %(klass)s is non-overlapping (no Intervals share
        points) and is either monotonic increasing or monotonic decreasing,
        else False.
        """
    # https://github.com/python/mypy/issues/1362
    # Mypy does not support decorated properties
    @property  # type: ignore
    @Appender(
        _interval_shared_docs["is_non_overlapping_monotonic"] % _shared_docs_kwargs
    )
    def is_non_overlapping_monotonic(self):
        # must be increasing  (e.g., [0, 1), [1, 2), [2, 3), ... )
        # or decreasing (e.g., [-1, 0), [-2, -1), [-3, -2), ...)
        # we already require left <= right

        # strict inequality for closed == 'both'; equality implies overlapping
        # at a point when both sides of intervals are included
        if self.closed == "both":
            return bool(
                (self.right[:-1] < self.left[1:]).all()
                or (self.left[:-1] > self.right[1:]).all()
            )

        # non-strict inequality when closed != 'both'; at least one side is
        # not included in the intervals, so equality does not imply overlapping
        return bool(
            (self.right[:-1] <= self.left[1:]).all()
            or (self.left[:-1] >= self.right[1:]).all()
        )

    # Conversion
    def __array__(self, dtype=None) -> np.ndarray:
        """
        Return the IntervalArray's data as a numpy array of Interval
        objects (with dtype='object')
        """
        left = self.left
        right = self.right
        mask = self.isna()
        closed = self._closed

        result = np.empty(len(left), dtype=object)
        for i in range(len(left)):
            if mask[i]:
                result[i] = np.nan
            else:
                result[i] = Interval(left[i], right[i], closed)
        return result

    def __arrow_array__(self, type=None):
        """
        Convert myself into a pyarrow Array.
        """
        import pyarrow
        from pandas.core.arrays._arrow_utils import ArrowIntervalType

        try:
            subtype = pyarrow.from_numpy_dtype(self.dtype.subtype)
        except TypeError as err:
            raise TypeError(
                f"Conversion to arrow with subtype '{self.dtype.subtype}' "
                "is not supported"
            ) from err
        interval_type = ArrowIntervalType(subtype, self.closed)
        storage_array = pyarrow.StructArray.from_arrays(
            [
                pyarrow.array(self.left, type=subtype, from_pandas=True),
                pyarrow.array(self.right, type=subtype, from_pandas=True),
            ],
            names=["left", "right"],
        )
        mask = self.isna()
        if mask.any():
            # if there are missing values, set validity bitmap also on the array level
            null_bitmap = pyarrow.array(~mask).buffers()[1]
            storage_array = pyarrow.StructArray.from_buffers(
                storage_array.type,
                len(storage_array),
                [null_bitmap],
                children=[storage_array.field(0), storage_array.field(1)],
            )

        if type is not None:
            if type.equals(interval_type.storage_type):
                return storage_array
            elif isinstance(type, ArrowIntervalType):
                # ensure we have the same subtype and closed attributes
                if not type.equals(interval_type):
                    raise TypeError(
                        "Not supported to convert IntervalArray to type with "
                        f"different 'subtype' ({self.dtype.subtype} vs {type.subtype}) "
                        f"and 'closed' ({self.closed} vs {type.closed}) attributes"
                    )
            else:
                raise TypeError(
                    f"Not supported to convert IntervalArray to '{type}' type"
                )

        return pyarrow.ExtensionArray.from_storage(interval_type, storage_array)

    _interval_shared_docs[
        "to_tuples"
    ] = """
        Return an %(return_type)s of tuples of the form (left, right).

        Parameters
        ----------
        na_tuple : bool, default True
            Returns NA as a tuple if True, ``(nan, nan)``, or just as the NA
            value itself if False, ``nan``.

            .. versionadded:: 0.23.0

        Returns
        -------
        tuples: %(return_type)s
        %(examples)s\
        """

    @Appender(
        _interval_shared_docs["to_tuples"] % dict(return_type="ndarray", examples="")
    )
    def to_tuples(self, na_tuple=True):
        tuples = com.asarray_tuplesafe(zip(self.left, self.right))
        if not na_tuple:
            # GH 18756
            tuples = np.where(~self.isna(), tuples, np.nan)
        return tuples

    @Appender(_extension_array_shared_docs["repeat"] % _shared_docs_kwargs)
    def repeat(self, repeats, axis=None):
        nv.validate_repeat(tuple(), dict(axis=axis))
        left_repeat = self.left.repeat(repeats)
        right_repeat = self.right.repeat(repeats)
        return self._shallow_copy(left=left_repeat, right=right_repeat)

    _interval_shared_docs["contains"] = textwrap.dedent(
        """
        Check elementwise if the Intervals contain the value.

        Return a boolean mask whether the value is contained in the Intervals
        of the %(klass)s.

        .. versionadded:: 0.25.0

        Parameters
        ----------
        other : scalar
            The value to check whether it is contained in the Intervals.

        Returns
        -------
        boolean array

        See Also
        --------
        Interval.contains : Check whether Interval object contains value.
        %(klass)s.overlaps : Check if an Interval overlaps the values in the
            %(klass)s.

        Examples
        --------
        %(examples)s
        >>> intervals.contains(0.5)
        array([ True, False, False])
    """
    )

    @Appender(
        _interval_shared_docs["contains"]
        % dict(
            klass="IntervalArray",
            examples=textwrap.dedent(
                """\
        >>> intervals = pd.arrays.IntervalArray.from_tuples([(0, 1), (1, 3), (2, 4)])
        >>> intervals
        <IntervalArray>
        [(0, 1], (1, 3], (2, 4]]
        Length: 3, closed: right, dtype: interval[int64]
        """
            ),
        )
    )
    def contains(self, other):
        if isinstance(other, Interval):
            raise NotImplementedError("contains not implemented for two intervals")

        return (self.left < other if self.open_left else self.left <= other) & (
            other < self.right if self.open_right else other <= self.right
        )

    _interval_shared_docs["overlaps"] = textwrap.dedent(
        """
        Check elementwise if an Interval overlaps the values in the %(klass)s.

        Two intervals overlap if they share a common point, including closed
        endpoints. Intervals that only have an open endpoint in common do not
        overlap.

        .. versionadded:: 0.24.0

        Parameters
        ----------
        other : %(klass)s
            Interval to check against for an overlap.

        Returns
        -------
        ndarray
            Boolean array positionally indicating where an overlap occurs.

        See Also
        --------
        Interval.overlaps : Check whether two Interval objects overlap.

        Examples
        --------
        %(examples)s
        >>> intervals.overlaps(pd.Interval(0.5, 1.5))
        array([ True,  True, False])

        Intervals that share closed endpoints overlap:

        >>> intervals.overlaps(pd.Interval(1, 3, closed='left'))
        array([ True,  True, True])

        Intervals that only have an open endpoint in common do not overlap:

        >>> intervals.overlaps(pd.Interval(1, 2, closed='right'))
        array([False,  True, False])
        """
    )

    @Appender(
        _interval_shared_docs["overlaps"]
        % dict(
            klass="IntervalArray",
            examples=textwrap.dedent(
                """\
        >>> data = [(0, 1), (1, 3), (2, 4)]
        >>> intervals = pd.arrays.IntervalArray.from_tuples(data)
        >>> intervals
        <IntervalArray>
        [(0, 1], (1, 3], (2, 4]]
        Length: 3, closed: right, dtype: interval[int64]
        """
            ),
        )
    )
    def overlaps(self, other):
        if isinstance(other, (IntervalArray, ABCIntervalIndex)):
            raise NotImplementedError
        elif not isinstance(other, Interval):
            msg = f"`other` must be Interval-like, got {type(other).__name__}"
            raise TypeError(msg)

        # equality is okay if both endpoints are closed (overlap at a point)
        op1 = le if (self.closed_left and other.closed_right) else lt
        op2 = le if (other.closed_left and self.closed_right) else lt

        # overlaps is equivalent negation of two interval being disjoint:
        # disjoint = (A.left > B.right) or (B.left > A.right)
        # (simplifying the negation allows this to be done in less operations)
        return op1(self.left, other.right) & op2(other.left, self.right)


def maybe_convert_platform_interval(values):
    """
    Try to do platform conversion, with special casing for IntervalArray.
    Wrapper around maybe_convert_platform that alters the default return
    dtype in certain cases to be compatible with IntervalArray.  For example,
    empty lists return with integer dtype instead of object dtype, which is
    prohibited for IntervalArray.

    Parameters
    ----------
    values : array-like

    Returns
    -------
    array
    """
    if isinstance(values, (list, tuple)) and len(values) == 0:
        # GH 19016
        # empty lists/tuples get object dtype by default, but this is
        # prohibited for IntervalArray, so coerce to integer instead
        return np.array([], dtype=np.int64)
    elif is_categorical_dtype(values):
        values = np.asarray(values)

    return maybe_convert_platform(values)
