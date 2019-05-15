# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 15:40:04
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-15 16:59:30

__all__ = [

    "DecisionMaker",
    "SingleDecisionMaker",

    ]

from ..action import Action

#{ BEGIN }#

class DecisionMaker(object):
    """
    决策者的抽象基类
    ----------------

    其具体派生类对特定的决策代码段进行封装
    实现对决策逻辑的拆分
    以此尝试提高决策树的清晰度，提高决策逻辑的复用性

    """


    def __init__(self, *args, **kwargs):
        if self.__class__ is __class__:
            raise NotImplementedError

    def _make_decision(self):
        """
        真正用于被派生类重载的抽象决策接口
        """
        raise NotImplementedError

    def make_decision(self):
        """
        [final] 决策接口，统一返回结果
        -----------------------------------

        - 如果真正的决策函数返回了一个有效的 action ，则将其作为最终结果直接返回

        - 如果返回结果为 None ，即决策函数判断到结尾，仍然没有找到任何一个合适于当前情况的行为
        则最终结果返回 INVALID action

        """
        res = self._make_decision()
        if isinstance(res, int): # 由 return 语句指定的返回值
            action = res
            return action
        elif isinstance(res, (tuple, list)): # 带信号的返回值
            assert len(res) == 2
            action, signal = res
            return ( action, signal ) # 直接返回无需教研
        elif res is None: # 空返回值
            action = Action.INVALID
            return action


class SingleDecisionMaker(DecisionMaker):
    """
    单人决策者的抽象基类，用于 Tank2Player 的个人决策

    """
    def __init__(self, player, signal, **kwargs):
        """
        重写的构造函数，确保与 Tank2Player._make_decision 接口的参数列表一致

        Input:
            - player   Tank2Player   单人玩家实例
            - signal   int           团队信号

        """
        self._player = player
        self._signal = signal

        if self.__class__ is __class__:
            raise NotImplementedError


#{ END }#