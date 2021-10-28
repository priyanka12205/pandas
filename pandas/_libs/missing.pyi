import numpy as np

from pandas._typing import npt

class C_NAType: ...
class NAType(C_NAType): ...

NA: NAType

def is_matching_na(
    left: object, right: object, nan_matches_none: bool = ...
) -> bool: ...
def isposinf_scalar(val: object) -> bool: ...
def isneginf_scalar(val: object) -> bool: ...
def checknull(val: object) -> bool: ...
def checknull_old(val: object) -> bool: ...
def isnaobj(arr: np.ndarray) -> npt.NDArray[np.bool_]: ...
def isnaobj_old(arr: np.ndarray) -> npt.NDArray[np.bool_]: ...
