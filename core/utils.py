# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-26 22:07:11
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 00:01:20
"""
工具类
"""

__all__ = [

    "debug_print",
    "debug_pprint",

    "simulator_print",
    "simulator_pprint",

    "outer_label",
    "memorize",

    "CachedProperty",
    "SingletonMeta",
    "UniqueIntEnumMeta",

    "DataSerializer",

    ]

from .const import DEBUG_MODE, SIMULATOR_ENV, SIMULATOR_PRINT
from .global_ import pprint, pickle, base64, gzip, contextmanager, hashlib, functools, types

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


@contextmanager
def outer_label():
    """
    用于直接打断外层循环，或者继续外层循环

    如果置于循环体之外，就是 break outer
    如果置于循环体之内，就是 continue outer
    """
    class _GotoOuterException(Exception):
        pass
    try:
        yield _GotoOuterException() # 每次创建后都不相同，嵌套的情况下，需要确保名称不相同
    except _GotoOuterException:     #　这样做是为了防止嵌套的情况下，无法从内层直接跳到最外层
        pass

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


def memorize(func):
    """
    根据参数列表缓存函数的返回值的修饰器
    ------------------------------------

    1. func 会以 __memory__ 缓存返回结果
    2. func 会带上 make_key 方法，可以用来获取传入参数列表对应的缓存 key
    3. func 会带上 clear_memory 方法，可以清空所有的缓存结果
    4. 如果返回值是生成器，会立即获得完整结果并转为 tuple 类型


    这个函数主要用于缓存搜索路径

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
            if isinstance(res, types.GeneratorType):
                res = list(res) # 如果返回结果是生成器，那么马上获得所有结果
            func.__memory__[key] = res
        return res

    wrapper.make_key = functools.partial(_make_key, func)
    wrapper.clear_memory = functools.partial(_clear_memory, func)

    return wrapper


class SingletonMeta(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
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