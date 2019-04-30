# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:22:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 00:08:12
"""
决策时的通用函数库

"""

__all__ = [

    #"get_destroyed_fields",

    "is_block_in_route",

    "fake_map_matrix_T_without_enemy",

    ]

from ..const import DIRECTIONS_URDL, DEBUG_MODE
from ..global_ import np, deque
from ..utils import debug_print, debug_pprint
from ..action import Action
from ..field import Field, EmptyField, SteelField, WaterField
from .bfs import MOVE_ACTION_ON_BFS, SHOOT_ACTION_ON_BFS

#{ BEGIN }#

''' # Migrate to BattleTank.get_destroyed_fields_if_shoot
def get_destroyed_fields(tank, action, map):
    """
    下一回合某坦克执行一个射击行为后，将会摧毁的 fields

    用于单向分析 action 所能造成的影响，不考虑对方下一回合的决策

    - 不判断自身是否与其他 tank 重叠
    - 如果对方是 tank 认为对方下回合不开炮

    Return:
        - fields   [Field]/[]   被摧毁的 fields
                                如果没有对象被摧毁，则返回空列表
    """
    map_ = map
    assert map_.is_valid_shoot_action(tank, action)

    action -= 4 # 使之与 dx, dy 的 idx 对应
    x, y = tank.xy
    dx, dy = Action.DIRECTION_OF_ACTION_XY[action]

    while True: # 查找该行/列上是否有可以被摧毁的对象
        x += dx
        y += dy
        if not map_.in_map(x, y):
            break
        currentFields = map_[x, y]
        if len(currentFields) == 0: # 没有对象
            continue
        elif len(currentFields) > 1: # 均为坦克
            return currentFields
        else: # len == 1
            field = currentFields[0]
            if isinstance(field, (WaterField, EmptyField) ): # 空对象或水路
                continue
            elif isinstance(field, SteelField): # 钢墙不可摧毁
                return []
            else:
                return currentFields

    return [] # 没有任何对象被摧毁
'''


def is_block_in_route(field, route):
    """
    判断一个 Brick/Base/Tank (具体由寻找路线时的函数决定) 是否为相应路线上，为一个
    block type 也就是必须要射击一次才能消灭掉的 field 对象。

    Input:
        - field    Field    地图上某个对象
        - route    [(x: int, y: int, weight: int, BFSAction: int)]   带权重值的路径
    """
    for x, y, weight, BFSAction in route:
        if (x, y) == field.xy:
            if weight >= 2 and BFSAction == MOVE_ACTION_ON_BFS: # 移动受阻的
                return True # 移动受阻，需要两个回合（及以上）
            elif weight >= 1 and BFSAction == SHOOT_ACTION_ON_BFS: # 射击受阻
                return True # 射击受阻，需要一个回合（及以上）（通常两回合，但是目标物可算作一回合）
    return False


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
        if cMatrixMap[oppTank.xy] == Field.TANK + 1 + oppSide:
            cMatrixMap[oppTank.xy] = Field.EMPTY
    return cMatrixMap

#{ END }#