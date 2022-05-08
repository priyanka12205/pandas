from typing import (
    Generic,
    TypeVar,
)

from pandas.core.indexing import IndexingMixin

_IndexingMixinT = TypeVar("_IndexingMixinT", bound=IndexingMixin)

class NDFrameIndexerBase(Generic[_IndexingMixinT]):
    name: str
    obj: _IndexingMixinT

    def __init__(self, name: str, obj: _IndexingMixinT) -> None: ...
    @property
    def ndim(self) -> int: ...
