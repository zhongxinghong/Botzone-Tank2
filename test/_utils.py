# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 04:45:39
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-04-29 01:56:02

__all__ = [

    "b", "u",

    "json_load",
    "to_stream",

    "cut_by_turn",

    ]

import json
from copy import deepcopy
from io import TextIOWrapper, BytesIO


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


def json_load(file):
    with open(file, "rb") as fp:
        return json.load(fp)


def to_stream(s):
    return TextIOWrapper(BytesIO(b(s)))


def cut_by_turn(inputJSON, turn=-1):
    """
    截短 json 数据

    使得最后一回合为第 turn 回合
    """
    if turn <= 0:
        return inputJSON

    maxTurn = len(inputJSON["responses"]) + 1 # 从 1 开始算起的 turn
    if turn > maxTurn:
        raise Exception("no such turn %s" % turn)

    res = deepcopy(inputJSON)
    res["requests"] = inputJSON["requests"][:turn-1+1] # 包含 header
    res["responses"] = inputJSON["responses"][:turn-1]

    return res
