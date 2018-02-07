#ifndef _PANDAS_MATH_H_
#define _PANDAS_MATH_H_

#if defined(_MSC_VER) && (_MSC_VER < 1800)
#include <cmath>
__inline int signbit(double num) { return _copysign(1.0, num) < 0; }
#else
#include <cmath>
#endif

#endif
