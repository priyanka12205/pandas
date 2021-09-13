from pandas._libs.util cimport numeric


cdef numeric kth_smallest_c(numeric* arr, Py_ssize_t k, Py_ssize_t n) nogil

cdef enum TiebreakEnumType:
    TIEBREAK_AVERAGE
    TIEBREAK_MIN,
    TIEBREAK_MAX
    TIEBREAK_FIRST
    TIEBREAK_FIRST_DESCENDING
    TIEBREAK_DENSE

tiebreakers = {
    "average": TIEBREAK_AVERAGE,
    "min": TIEBREAK_MIN,
    "max": TIEBREAK_MAX,
    "first": TIEBREAK_FIRST,
    "dense": TIEBREAK_DENSE,
}
