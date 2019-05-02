# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 22:14:37
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-03 03:57:35
"""
消息与信号

用于通知队友

"""

__all__ = [

    "Signal",

    ]

from ..utils import UniqueIntEnumMeta

#{ BEGIN }#

class Signal(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 200

    NONE        = 0   # 空信号
    UNHANDLED   = 1   # 未处理团队信号，通常是因为有更紧急的状况而没有运行到相应的处理信号的位置
    CANHANDLED  = 2   # 未能处理团队信号，通常是因为尝试处理但是发现不合适


    PREPARE_FOR_BREAK_BRICK = 11 # 准备破墙，也就是准备给自己寻找后路
    READY_TO_PREPARE_FOR_BREAK_BRICK = 12 # 准备好为破墙而凿开两边墙壁
    READY_TO_BREAK_BRICK = 13  # 准备要破墙


    PREPARE_FOR_BREAK_OVERLAP = 14  # 团队向队员发信号，希望能马上打破重叠
    READY_TO_BREAK_OVERLAP    = 15  # 准备要主动打破重叠


    BREAK_SIGNALS = ( UNHANDLED, CANHANDLED )

    @staticmethod
    def is_break(signal):
        """
        该信号是否意味着沟通停止
        也就是是否为未处理或无法处理
        """
        return signal in __class__.BREAK_SIGNALS

#{ END }#