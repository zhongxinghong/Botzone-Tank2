# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 11:41:05
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 13:35:13

__all__ = [

    "cut_by_turn",

    ]

from copy import deepcopy


def cut_by_turn(inputJSON, turn=-1):
    """
    截短 json 数据，使得最后一回合为第 turn 回合
    如果 turn == -1 则返回全部数据
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