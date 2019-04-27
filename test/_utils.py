# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 04:45:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 05:07:45

__all__ = [

    "b", "u",

    "to_stream",
    "json_load",

    ]

from io import TextIOWrapper, BytesIO
import json


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

def to_stream(s):
    return TextIOWrapper(BytesIO(b(s)))

def json_load(file):
    with open(file, "rb") as fp:
        return json.load(fp)


