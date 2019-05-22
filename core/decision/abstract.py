# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 15:40:04
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-21 20:57:24

__all__ = [

    "DecisionMaker",
    "SingleDecisionMaker",
    "RespondTeamSignalDecisionMaker",

    ]

from ..action import Action
from ..strategy.signal import Signal

#{ BEGIN }#

class DecisionMaker(object):
    """
    决策者的抽象基类
    ----------------

    泛指一切具有决策能力的对象，可以是具象的，例如 Team, Player
    也可以是抽象的，例如决策类

    该类的派生类对特定的决策代码段进行封装

    如果派生类是决策类，那么将实现对决策逻辑的拆分，以此来提高决策树的清晰度，提高决策逻辑的复用性

    """
    UNHANDLED_RESULT = None

    def __init__(self, *args, **kwargs):
        if self.__class__ is __class__:
            raise NotImplementedError

    def is_handled(self, result):
        """
        用于判断决策对象返回的结果是否标志着该决策适用于当前情况，用于被外部判断

        规定当该决策对象不能 handle 时，返回 __class__.UNHANDLED_RESULT
        那么只需要判断实际返回值是否与之相等，即可判断该情况是否被 handle

        """
        return result != self.__class__.UNHANDLED_RESULT

    def _make_decision(self):
        """
        真正用于被派生类重载的抽象决策接口

        如果该情况不适用，那么不需要写任何返回值，函数默认返回 None
        make_decision 函数将以此来判断该情况是否被 handle

        """
        raise NotImplementedError

    def make_decision(self):
        """
        外部可调用的决策接口
        ----------------------
        会对 _make_decision 的结果进行一些统一的处理，也可以用于在决策前后进行一些预处理和后处理操作

        此处提供一个默认的情况的处理方法：
        ----------------------------------
        - 如果真正的决策函数返回了一个 action ，则将其作为最终结果直接返回
        - 如果当前情况不适用，真正的决策函数返回了 None ，则返回 UNHANDLED_RESULT

        """
        res = self._make_decision()
        if res is None:
            return self.__class__.UNHANDLED_RESULT
        return res


class SingleDecisionMaker(DecisionMaker):
    """
    单人决策者的抽象基类，用于 Tank2Player 的个人决策

    """
    UNHANDLED_RESULT = Action.INVALID

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


class RespondTeamSignalDecisionMaker(SingleDecisionMaker):
    """
    用于处理团队信号的决策模型

    注意：
    ------------

    """
    UNHANDLED_RESULT = ( Action.INVALID, Signal.INVALID )
    HANDLED_SIGNALS  = (  ) # 将会处理到的团队信号

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.__class__ is __class__:
            raise NotImplementedError

    def make_decision(self):
        """
        通常来说，如果团队发送了一个信号，必须及时返回一个结果
        只有在 signal is None 的情况下，才返回 UNHANDLED_RESULT

        """
        res = self._make_decision()
        if res is None:
            signal = self._signal
            if signal in self.__class__.HANDLED_SIGNALS: # 团队信号必须得到响应
                raise Exception("team signal %d must be responded" % signal)
            return self.__class__.UNHANDLED_RESULT
        return res


#{ END }#