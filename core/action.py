# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:28:59
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 15:53:38
"""
行为类
"""

__all__ = [

    "Action",

    ]

#{ BEGIN }#

class Action(object):

    DUMMY       = -3
    INVALID     = -2
    STAY        = -1
    MOVE_UP     = 0
    MOVE_RIGHT  = 1
    MOVE_DOWN   = 2
    MOVE_LEFT   = 3
    SHOOT_UP    = 4
    SHOOT_RIGHT = 5
    SHOOT_DOWN  = 6
    SHOOT_LEFT  = 7

    # 根据 action 的值判断移动方向和射击方向
    DIRECTION_OF_ACTION_X  = (  0, 1, 0, -1 )
    DIRECTION_OF_ACTION_Y  = ( -1, 0, 1,  0 )

    @staticmethod
    def is_move(action):
        """
        是否为移动行动
        """
        return 0 <= action <= 3

    @staticmethod
    def is_shoot(action):
        """
        是否为射击行动
        """
        return 4 <= action <= 7

    @staticmethod
    def is_opposite(action1, action2):
        """
        两个行动方向是否相对

        注： 此处不检查两个行为是否均与方向有关，即均处于 [0, 7] 范围内
        """
        return action1 % 4 == (action2 + 2) % 4

    @staticmethod
    def get_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的 move 行为值
        """
        dx = x2 - x1
        dy = y2 - y1

        if dx == dy == 0:
            return __class__.STAY

        for idx, dxy in enumerate(zip(__class__.DIRECTION_OF_ACTION_X,
                                      __class__.DIRECTION_OF_ACTION_Y)):
            if (dx, dy) == dxy:
                return idx
        else:
            raise Exception("can't move from (%s, %s) to (%s, %s) in one step"
                             % (x1, y1, x2, y2) )

#{ END }#