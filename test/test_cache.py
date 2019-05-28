# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-28 01:19:15
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-28 23:57:25

from functools import lru_cache
from functools import wraps
import functools
import numpy as np
import pickle
import hashlib
from types import GeneratorType
import inspect

aa = np.arange(9).reshape((3,3))
bb = aa.copy()

a = (1, 2)
b = (3, 4)
c = aa
d = True
e = False

_args = (a, b, c, d, e)
_kwargs1 = {"f": True, "g": False}
_kwargs2 = {"g": False, "f": True}

print(pickle.dumps(_kwargs1) == pickle.dumps(_kwargs2))
print(pickle.dumps(sorted(_kwargs1)) == pickle.dumps(sorted(_kwargs2)))


class _Missing(object):
    """
    from werkzeug._internal
    """
    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'


_MISSING = _Missing()


def memorize(func):
    """
    根据参数列表缓存函数的返回值的修饰器

    1. func 会以 __memory__ 缓存返回结果
    2. func 会带上 make_key 方法，可以用来获取传入参数列表对应的缓存 key
    3. func 会带上 clear_memory 方法，可以清空所有的缓存结果

    """
    def _make_key(func, *args, **kwargs):
        _key = (
            func.__module__,
            func.__name__,
            args,
            sorted(kwargs.items()) # kwargs 自动排序
        )
        return hashlib.md5(pickle.dumps(_key)).hexdigest()

    def _clear_memory(func):
        if hasattr(func, "__memory__"):
            func.__memory__.clear()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(func, "__memory__"):
            func.__memory__ = {}
        key = _make_key(func, *args, **kwargs)
        res = func.__memory__.get(key, _MISSING)
        if res is _MISSING:
            res = func(*args, **kwargs)
            if isinstance(res, GeneratorType):
                res = list(res)
            func.__memory__[key] = res
        return res

    wrapper.make_key = functools.partial(_make_key, func)
    wrapper.clear_memory = functools.partial(_clear_memory, func)

    return wrapper


def a(*args, **kwargs):
    print("a.__call__")
    return 1

b = memorize(a)

print("call a()")
for _ in range(3):
    r = a(*_args, **_kwargs1)
    print(r)

print("call b()")
for _ in range(3):
    r = b(*_args, **_kwargs1)
    print(r)
    r = b(*_args, **_kwargs2)
    print(r)
    b.clear_memory()
    print("b.clear_memory")
    r = b(*_args, **_kwargs2)
    print(r)

print(b.__wrapped__.__dict__)
print(b.make_key(*_args, **_kwargs1))

@memorize
def c(*args, **kwargs):
    yield from range(9)

for _ in range(3):
    print("call c()")
    for i in c():
        print(i)
