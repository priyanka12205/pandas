from datetime import (
    date as _date,
    datetime,
    time as _time,
    timedelta,
    tzinfo as _tzinfo,
)
from time import struct_time
from typing import (
    ClassVar,
    Type,
    TypeVar,
    overload,
)

import numpy as np

from pandas._libs.tslibs import (
    BaseOffset,
    NaT,
    NaTType,
    Period,
    Timedelta,
)

_S = TypeVar("_S")

def integer_op_not_supported(obj) -> None: ...

class Timestamp(datetime):
    min: ClassVar[Timestamp]
    max: ClassVar[Timestamp]

    resolution: ClassVar[Timedelta]
    value: int  # np.int64

    # error: "__new__" must return a class instance (got "Union[Timestamp, NaTType]")
    def __new__(  # type: ignore[misc]
        cls: Type[_S],
        ts_input: int
        | np.integer
        | float
        | str
        | _date
        | datetime
        | np.datetime64 = ...,
        freq=...,
        tz: str | _tzinfo | None | int = ...,
        unit=...,
        year: int | None = ...,
        month: int | None = ...,
        day: int | None = ...,
        hour: int | None = ...,
        minute: int | None = ...,
        second: int | None = ...,
        microsecond: int | None = ...,
        nanosecond: int | None = ...,
        tzinfo: _tzinfo | None = ...,
        *,
        fold: int | None = ...,
    ) -> _S | NaTType: ...
    def _set_freq(self, freq: BaseOffset | None) -> None: ...
    @property
    def year(self) -> int: ...
    @property
    def month(self) -> int: ...
    @property
    def day(self) -> int: ...
    @property
    def hour(self) -> int: ...
    @property
    def minute(self) -> int: ...
    @property
    def second(self) -> int: ...
    @property
    def microsecond(self) -> int: ...
    @property
    def tzinfo(self) -> _tzinfo | None: ...
    @property
    def tz(self) -> _tzinfo | None: ...
    @property
    def fold(self) -> int: ...
    @classmethod
    def fromtimestamp(cls: Type[_S], t: float, tz: _tzinfo | None = ...) -> _S: ...
    @classmethod
    def utcfromtimestamp(cls: Type[_S], t: float) -> _S: ...
    @classmethod
    def today(cls: Type[_S]) -> _S: ...
    @classmethod
    def fromordinal(cls: Type[_S], n: int) -> _S: ...
    @classmethod
    def now(cls: Type[_S], tz: _tzinfo | str | None = ...) -> _S: ...
    @classmethod
    def utcnow(cls: Type[_S]) -> _S: ...
    @classmethod
    def combine(
        cls, date: _date, time: _time, tzinfo: _tzinfo | None = ...
    ) -> datetime: ...
    @classmethod
    def fromisoformat(cls: Type[_S], date_string: str) -> _S: ...
    def strftime(self, fmt: str) -> str: ...
    def __format__(self, fmt: str) -> str: ...
    def toordinal(self) -> int: ...
    def timetuple(self) -> struct_time: ...
    def timestamp(self) -> float: ...
    def utctimetuple(self) -> struct_time: ...
    def date(self) -> _date: ...
    def time(self) -> _time: ...
    def timetz(self) -> _time: ...
    def replace(
        self,
        year: int = ...,
        month: int = ...,
        day: int = ...,
        hour: int = ...,
        minute: int = ...,
        second: int = ...,
        microsecond: int = ...,
        tzinfo: _tzinfo | None = ...,
        *,
        fold: int = ...,
    ) -> datetime: ...
    def astimezone(self: _S, tz: _tzinfo | None = ...) -> _S: ...
    def ctime(self) -> str: ...
    def isoformat(self, sep: str = ..., timespec: str = ...) -> str: ...
    @classmethod
    def strptime(cls, date_string: str, format: str) -> datetime: ...
    def utcoffset(self) -> timedelta | None: ...
    def tzname(self) -> str | None: ...
    def dst(self) -> timedelta | None: ...
    # error: Argument 1 of "__le__" is incompatible with supertype "date";
    # supertype defines the argument type as "date"
    def __le__(self, other: datetime) -> bool: ...  # type: ignore
    # error: Argument 1 of "__lt__" is incompatible with supertype "date";
    # supertype defines the argument type as "date"
    def __lt__(self, other: datetime) -> bool: ...  # type: ignore
    # error: Argument 1 of "__ge__" is incompatible with supertype "date";
    # supertype defines the argument type as "date"
    def __ge__(self, other: datetime) -> bool: ...  # type: ignore
    # error: Argument 1 of "__gt__" is incompatible with supertype "date";
    # supertype defines the argument type as "date"
    def __gt__(self, other: datetime) -> bool: ...  # type: ignore
    def __add__(self: _S, other: timedelta) -> _S: ...
    def __radd__(self: _S, other: timedelta) -> _S: ...
    @overload  # type: ignore
    def __sub__(self, other: datetime) -> timedelta: ...
    @overload
    def __sub__(self, other: timedelta) -> datetime: ...
    def __hash__(self) -> int: ...
    def weekday(self) -> int: ...
    def isoweekday(self) -> int: ...
    def isocalendar(self) -> tuple[int, int, int]: ...
    @property
    def is_leap_year(self) -> bool: ...
    @property
    def is_month_start(self) -> bool: ...
    @property
    def is_quarter_start(self) -> bool: ...
    @property
    def is_year_start(self) -> bool: ...
    @property
    def is_month_end(self) -> bool: ...
    @property
    def is_quarter_end(self) -> bool: ...
    @property
    def is_year_end(self) -> bool: ...
    def to_pydatetime(self, warn: bool = ...) -> datetime: ...
    def to_datetime64(self) -> np.datetime64: ...
    def to_period(self, freq) -> Period: ...
    def to_julian_date(self) -> np.float64: ...
    @property
    def asm8(self) -> np.datetime64: ...
    def tz_convert(self: _S, tz) -> _S: ...
    # TODO: could return NaT?
    def tz_localize(
        self: _S, tz, ambiguous: str = ..., nonexistent: str = ...
    ) -> _S: ...
    def normalize(self: _S) -> _S: ...
    # TODO: round/floor/ceil could return NaT?
    def round(
        self: _S, freq, ambiguous: bool | str = ..., nonexistent: str = ...
    ) -> _S: ...
    def floor(
        self: _S, freq, ambiguous: bool | str = ..., nonexistent: str = ...
    ) -> _S: ...
    def ceil(
        self: _S, freq, ambiguous: bool | str = ..., nonexistent: str = ...
    ) -> _S: ...
