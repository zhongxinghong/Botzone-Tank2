# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-26 22:07:11
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 18:59:45
"""
工具类
"""

__all__ = [

    "debug_print",
    "debug_pprint",

    "CachedProperty",
    "Singleton",

    ]

from .const import DEBUG_MODE, LONG_RUNNING_MODE
from .global_ import pprint

#{ BEGIN }#

if DEBUG_MODE:
    debug_print  = print
    debug_pprint = pprint
else:
    debug_print  = lambda *args, **kwargs: None
    debug_pprint = debug_print


class _Missing(object):
    """
    from werkzeug._internal
    """

    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_MISSING = _Missing()


class CachedProperty(property):
    """
    from werkzeug.utils
    """

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _MISSING)
        if value is _MISSING:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

    @staticmethod
    def clean(obj, key):
        """
        清除缓存
        """
        obj.__dict__.pop(key, None)


class Singleton(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(Singleton, cls).__call__(*args)
        return cls._instance[cls]

#{ END }#