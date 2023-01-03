"""
Tests for the `deprecate_nonkeyword_arguments` decorator
"""

import inspect
import warnings

from pandas.util._decorators import deprecate_nonkeyword_arguments

import pandas._testing as tm

from pandas.core.groupby.generic import (
    skew,
    take,
)
from pandas.core.groupby.groupby import (
    cummax,
    cummin,
    cumprod,
    cumsum,
)



@deprecate_nonkeyword_arguments(
    version="1.1", allowed_args=["a", "b"], name="f_add_inputs"
)
def f(a, b=0, c=0, d=0):
    return a + b + c + d


def test_f_signature():
    assert str(inspect.signature(f)) == "(a, b=0, *, c=0, d=0)"


def test_one_argument():
    with tm.assert_produces_warning(None):
        assert f(19) == 19


def test_one_and_one_arguments():
    with tm.assert_produces_warning(None):
        assert f(19, d=6) == 25


def test_two_arguments():
    with tm.assert_produces_warning(None):
        assert f(1, 5) == 6


def test_two_and_two_arguments():
    with tm.assert_produces_warning(None):
        assert f(1, 3, c=3, d=5) == 12


def test_three_arguments():
    with tm.assert_produces_warning(FutureWarning):
        assert f(6, 3, 3) == 12


def test_four_arguments():
    with tm.assert_produces_warning(FutureWarning):
        assert f(1, 2, 3, 4) == 10


def test_three_arguments_with_name_in_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert f(6, 3, 3) == 12
        assert len(w) == 1
        for actual_warning in w:
            assert actual_warning.category == FutureWarning
            assert str(actual_warning.message) == (
                "Starting with pandas version 1.1 all arguments of f_add_inputs "
                "except for the arguments 'a' and 'b' will be keyword-only."
            )


@deprecate_nonkeyword_arguments(version="1.1")
def g(a, b=0, c=0, d=0):
    with tm.assert_produces_warning(None):
        return a + b + c + d


def test_g_signature():
    assert str(inspect.signature(g)) == "(a, *, b=0, c=0, d=0)"


def test_one_and_three_arguments_default_allowed_args():
    with tm.assert_produces_warning(None):
        assert g(1, b=3, c=3, d=5) == 12


def test_three_arguments_default_allowed_args():
    with tm.assert_produces_warning(FutureWarning):
        assert g(6, 3, 3) == 12


def test_three_positional_argument_with_warning_message_analysis():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert g(6, 3, 3) == 12
        assert len(w) == 1
        for actual_warning in w:
            assert actual_warning.category == FutureWarning
            assert str(actual_warning.message) == (
                "Starting with pandas version 1.1 all arguments of g "
                "except for the argument 'a' will be keyword-only."
            )


@deprecate_nonkeyword_arguments(version="1.1")
def h(a=0, b=0, c=0, d=0):
    return a + b + c + d


def test_h_signature():
    assert str(inspect.signature(h)) == "(*, a=0, b=0, c=0, d=0)"


def test_all_keyword_arguments():
    with tm.assert_produces_warning(None):
        assert h(a=1, b=2) == 3


def test_one_positional_argument():
    with tm.assert_produces_warning(FutureWarning):
        assert h(23) == 23


def test_one_positional_argument_with_warning_message_analysis():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert h(19) == 19
        assert len(w) == 1
        for actual_warning in w:
            assert actual_warning.category == FutureWarning
            assert str(actual_warning.message) == (
                "Starting with pandas version 1.1 all arguments "
                "of h will be keyword-only."
            )


@deprecate_nonkeyword_arguments(version="1.1")
def i(a=0, /, b=0, *, c=0, d=0):
    return a + b + c + d


def test_i_signature():
    assert str(inspect.signature(i)) == "(*, a=0, b=0, c=0, d=0)"


class Foo:
    @deprecate_nonkeyword_arguments(version=None, allowed_args=["self", "bar"])
    def baz(self, bar=None, foobar=None):  # pylint: disable=disallowed-name
        ...


def test_foo_signature():
    assert str(inspect.signature(Foo.baz)) == "(self, bar=None, *, foobar=None)"


def test_class():
    msg = (
        r"In a future version of pandas all arguments of Foo\.baz "
        r"except for the argument \'bar\' will be keyword-only"
    )
    with tm.assert_produces_warning(FutureWarning, match=msg):
        Foo().baz("qux", "quox")


def test_deprecated_keywords():
    msg=(
        "In the future version of pandas the arguments args"
        "and kwargs will be deprecated for these functions"
    )
    with tm.assert_produces_warning(FutureWarning, match=msg):
        assert cummax
        assert cummin
        assert cumprod
        assert cumsum
        assert skew
        assert take
