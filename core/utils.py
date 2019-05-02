# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-26 22:07:11
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-02 14:18:50
"""
工具类
"""

__all__ = [

    "debug_print",
    "debug_pprint",

    "simulator_print",
    "simulator_pprint",

    "CachedProperty",
    "SingletonMeta",
    "UniqueIntEnumMeta",

    "DataSerializer",

    ]

from .const import DEBUG_MODE, SIMULATOR_ENV, SIMULATOR_PRINT
from .global_ import pprint, pickle, base64, gzip

#{ BEGIN }#

_null_func = lambda *args, **kwargs: None

if DEBUG_MODE:
    debug_print  = print
    debug_pprint = pprint
else:
    debug_print  = _null_func
    debug_pprint = _null_func

if SIMULATOR_ENV and SIMULATOR_PRINT:
    simulator_print  = print
    simulator_pprint = pprint
else:
    simulator_print  = _null_func
    simulator_pprint = _null_func


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


class SingletonMeta(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(SingletonMeta, cls).__call__(*args)
        return cls._instance[cls]


class UniqueIntEnumMeta(type):
    """
    使得枚举类内所有的 int 值都增加一个 __offset__ 偏移量
    使得不同的枚举类可以用同样的 int 值申明 case，但是不同枚举类间，实际的属性值不同不同

    需要在类属性中通过 __offset__ 值申明偏移量

    """
    def __new__(cls, name, bases, attrs):
        offset = attrs.get("__offset__", 0) # 默认为 0
        for k, v in attrs.items():
            if isinstance(v, int):
                attrs[k] += offset
        return super(UniqueIntEnumMeta, cls).__new__(cls, name, bases, attrs)


class DataSerializer(object):

    @staticmethod
    def _unpad(s):
        return s.rstrip("=")

    @staticmethod
    def _pad(s):
        return s + "=" * ( 4 - len(s) % 4 )

    @staticmethod
    def serialize(obj):
        return __class__._unpad(
                    base64.b64encode(
                        gzip.compress(
                            pickle.dumps(obj))).decode("utf-8"))

    @staticmethod
    def deserialize(s):
        return pickle.loads(
                    gzip.decompress(
                        base64.b64decode(
                            __class__._pad(s).encode("utf-8"))))

#{ END }#