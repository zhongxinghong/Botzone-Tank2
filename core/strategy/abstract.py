# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:20:10
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 12:17:02
"""
策略类的抽象接口
"""

__all__ = [

    "SingleTankStrategy",

    ]

#{ BEGIN }#

class Strategy(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
        raise NotImplementedError


class SingleTankStrategy(Strategy):
    """
    不考虑其他 tank 的情况，某一 tank 单独决策

    """
    def __init__(self, tank, map, **kwargs):
        """
        Input:
            - tank   TankField   需要做出决策的 tank
            - map    Tank2Map    当前地图
        """
        self._tank = tank
        self._map = map

    def make_decision(self, *args, **kwargs):
        """
        该 tank 单独做出决策

        Return:
            - action   int   Action 类中定义的动作编号
                             如果判断到在这种情况下不适合使用该策略，则返回 Action.INVALID
        """
        raise NotImplementedError


#{ END }#