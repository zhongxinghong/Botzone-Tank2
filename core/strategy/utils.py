# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:22:20
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-28 02:30:23
"""
决策时的通用函数库

"""

__all__ = [

    "fake_map_matrix_T_without_enemy",
    "fake_map_matrix_T_thinking_of_enemy_as_steel",

    "get_manhattan_distance",

    ]

from ..const import DEBUG_MODE
from ..global_ import np, deque
from ..utils import debug_print, debug_pprint
from ..action import Action
from ..field import Field, EmptyField, SteelField, WaterField

#{ BEGIN }#

def fake_map_matrix_T_without_enemy(map, mySide):
    """
    伪造一个没有敌方坦克的地图类型矩阵

    WARNING:
        首先检查是不是对方 tank ，因为可能遇到对方已经死亡或者两方坦克重合
        这种时候如果己方坦克恰好在这个位置，就会被删掉，assert 不通过
    """
    map_ = map
    oppSide = 1 - mySide
    cMatrixMap = map_.matrix_T.copy()
    for oppTank in map_.tanks[oppSide]:
        if (cMatrixMap[oppTank.xy] == Field.TANK + 1 + oppSide
            or cMatrixMap[oppTank.xy] == Field.MULTI_TANK # 还需要考虑重叠的坦克
            ):
            cMatrixMap[oppTank.xy] = Field.EMPTY
    return cMatrixMap


def fake_map_matrix_T_thinking_of_enemy_as_steel(map, mySide):
    """
    伪造一个敌方坦克视为钢墙的地图类型矩阵
    用于在堵路时估计对方时候存在绕路的可能
    """
    map_ = map
    oppSide = 1 - mySide
    cMatrixMap = map_.matrix_T.copy()
    for oppTank in map_.tanks[oppSide]:
        if (cMatrixMap[oppTank.xy] == Field.TANK + 1 + oppSide
            or cMatrixMap[oppTank.xy] == Field.MULTI_TANK # 还需要考虑重叠的坦克
            ):
            cMatrixMap[oppTank.xy] = Field.STEEL
    return cMatrixMap


def get_manhattan_distance(x1, y1, x2, y2):
    """
    获得 (x1, y1) -> (x2, y2) 曼哈顿距离
    """
    return np.abs(x1 - x2) + np.abs(y1 - y2)

#{ END }#