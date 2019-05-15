# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 15:40:51
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-15 16:53:37

__all__ = [

    "DecisionChain",

    ]

from ..action import Action
from .abstract import DecisionMaker


#{ BEGIN }#

class DecisionChain(DecisionMaker):
    """
    决策链
    -------------

    效仿责任链模式，对多个决策实例进行组合，按优先级顺序依次进行决策
    如果遇到一个符合条件的决策，则将其决策结果返回，否则继续尝试低优先级的决策

    """
    def __init__(self, *decisions):
        self._decisions = decisions
        for decision in self._decisions: # 确保所有的 decision 实例均为 DecisionMaker 的派生
            assert isinstance(decision, DecisionMaker)

    def _make_decision(self):
        for decision in self._decisions:
            action = decision.make_decision()
            if not ( isinstance(action, int) and not Action.is_valid(action) ):
                return action

#{ END }#