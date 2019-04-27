# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:20:10
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 16:30:30
"""
策略类的抽象接口
"""

__all__ = [

    "Strategy",

    ]

#{ BEGIN }#

class Strategy(object):

    def __init__(self, tank, map, **kwargs):
        """
        Input:
            - tank   TankField   需要做出决策的 tank
            - map    Tank2Map    当前地图
        """
        self._tank = tank
        self._map = map

    def make_decision(self):
        """
        做出决策

        Return:
            - action   int   Action 类中定义的动作编号
        """
        raise NotImplementedError

#{ END }#