# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:28:59
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-03 20:49:01
"""
行为类
"""

__all__ = [

    "Action",

    ]

from .global_ import np
from .utils import debug_print

#{ BEGIN }#

class Action(object):

    # 推迟决策
    POSTPONE    = -4 # 用于告知 Team 让队友优先决策

    # 空与无效
    DUMMY       = -3 # 额外添加的
    INVALID     = -2

    # 停止
    STAY        = -1

    # 移动
    MOVE_UP     = 0
    MOVE_RIGHT  = 1
    MOVE_DOWN   = 2
    MOVE_LEFT   = 3

    # 射击
    SHOOT_UP    = 4
    SHOOT_RIGHT = 5
    SHOOT_DOWN  = 6
    SHOOT_LEFT  = 7

    # 根据 action 的值判断移动方向和射击方向
    DIRECTION_OF_ACTION_X  = (  0, 1, 0, -1 )
    DIRECTION_OF_ACTION_Y  = ( -1, 0, 1,  0 )
    DIRECTION_OF_ACTION_XY = ( (0,-1), (1,0), (0,1), (-1,0) )

    # 方便用于迭代
    MOVE_ACTIONS  = ( MOVE_UP,  MOVE_RIGHT,  MOVE_DOWN,  MOVE_LEFT  )
    SHOOT_ACTIONS = ( SHOOT_UP, SHOOT_RIGHT, SHOOT_DOWN, SHOOT_LEFT )
    VALID_ACTIONS = ( STAY, ) + MOVE_ACTIONS + SHOOT_ACTIONS


    _ACTION_NAMES = [

        "Invalid",  "Stay",
        "Up Move",  "Right Move",  "Down Move",  "Left Move",
        "Up Shoot", "Right Shoot", "Down Shoot", "Left Shoot",

        ]

    @staticmethod
    def is_valid(action): # 是否为有效行为
        return -1 <= action <= 7

    @staticmethod
    def is_stay(action): # 是否为停止行为
        return action == -1

    @staticmethod
    def is_move(action): # 是否为移动行为
        return 0 <= action <= 3

    @staticmethod
    def is_shoot(action): # 是否为射击行为
        return 4 <= action <= 7

    @staticmethod
    def is_opposite(action1, action2):
        """
        两个行动方向是否相对
        """
        if action1 == -1 or action2 == -1:
            return False
        return action1 % 4 == (action2 + 2) % 4

    @staticmethod
    def is_same_direction(action1, action2):
        """
        两个行动方向是否相同
        """
        if action1 == -1 or action2 == -1:
            return False
        return action1 % 4 == action2 % 4

    @staticmethod
    def get_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的 move 行为值
        可以不相邻！
        """
        dx = np.sign(x2 - x1)
        dy = np.sign(y2 - y1)

        if dx == dy == 0:
            return -1 # STAY

        for idx, dxy in enumerate(__class__.DIRECTION_OF_ACTION_XY):
            if (dx, dy) == dxy:
                return idx
        else:
            raise Exception("can't move from (%s, %s) to (%s, %s) in one turn"
                             % (x1, y1, x2, y2) )

    @staticmethod
    def get_move_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的射击行为
        这个就是对 get_action 的命名，这出于历史遗留问题 ...
        """
        return __class__.get_action(x1, y1, x2, y2)

    @staticmethod
    def get_shoot_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的射击行为
        """
        return __class__.get_action(x1, y1, x2, y2) + 4

    @staticmethod
    def get_name(action):
        return __class__._ACTION_NAMES[action + 2]

#{ END }#