# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 06:10:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 02:25:35

__all__ = [

    "mkdir",
    "abs_path",

    "read_file",

    "json_load",
    "json_dump",

    "Singleton",

    ]


import os

try:
    from requests.compat import json
except ModuleNotFoundError:
    import json


_ROOT_DIR = os.path.join(os.path.dirname(__file__), "../") # tools/ 为根目录

def mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

def abs_path(*path):
    return os.path.abspath(os.path.join(_ROOT_DIR, *path))

def read_file(file, encoding="utf-8-sig"):
    with open(file, "r", encoding=encoding) as fp:
        return fp.read()


def json_load(file, *args, **kwargs):
    if not file:
        return None
    elif not os.path.exists(file):
        return None
    else:
        with open(file, "r", encoding="utf-8-sig") as fp:
            try:
                return json.load(fp, *args, **kwargs)
            except json.JSONDecodeError:
                return None

def json_dump(obj, file, *args, **kwargs):
    encoding = kwargs.pop("encoding", "utf-8")
    with open(file, "w", encoding=encoding) as fp:
        json.dump(obj, fp, *args, **kwargs)


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