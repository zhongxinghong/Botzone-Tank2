# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 06:10:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-21 15:30:34

__all__ = [

    "mkdir",
    "get_abspath",

    "read_file",

    "json_load",
    "json_dump",

    "b",
    "u",

    "Singleton",

    "CachedProperty",

    ]


import os
from requests.compat import json


__ROOT_DIR = os.path.join(os.path.dirname(__file__), "../") # tools/ 为根目录


def mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

def get_abspath(*path):
    return os.path.abspath(os.path.join(__ROOT_DIR, *path))

def read_file(file, encoding="utf-8-sig"):
    with open(file, "r", encoding=encoding) as fp:
        return fp.read()

def json_load(file, **kwargs):
    with open(file, "r", encoding="utf-8-sig") as fp:
        return json.load(fp, **kwargs)

def json_dump(obj, file, **kwargs):
    encoding = kwargs.pop("encoding", "utf-8")
    with open(file, "w", encoding=encoding) as fp:
        json.dump(obj, fp, **kwargs)

def b(s):
    """
    bytes/str/int/float -> bytes
    """
    if isinstance(s, bytes):
        return s
    elif isinstance(s, (str,int,float)):
        return str(s).encode("utf-8")
    else:
        raise TypeError(s)

def u(s):
    """
    bytes/str/int/float -> str(utf8)
    """
    if isinstance(s, (str,int,float)):
        return str(s)
    elif isinstance(s, bytes):
        return s.decode("utf-8")
    else:
        raise TypeError(s)


class Singleton(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _inst = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._inst:
            cls._inst[cls] = super(Singleton, cls).__call__(*args)
        return cls._inst[cls]


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