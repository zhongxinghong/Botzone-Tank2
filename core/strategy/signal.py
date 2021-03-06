# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 22:14:37
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-26 18:34:31
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

    INVALID     = -1  # 无效信号
    NONE        = 0   # 空信号
    UNHANDLED   = 1   # 未处理团队信号，通常是因为有更紧急的状况而没有运行到相应的处理信号的位置
    CANHANDLED  = 2   # 未能处理团队信号，通常是因为尝试处理但是发现不合适


    PREPARE_FOR_BREAK_BRICK          = 11  # 团队信号，准备破墙，先给自己寻找后路
    READY_TO_PREPARE_FOR_BREAK_BRICK = 12  # 队员信号，准备好为破墙而凿开两边墙壁

    FORCED_TO_BREAK_BRICK            = 13  #　团队信号，强制破墙
    READY_TO_BREAK_BRICK             = 14  # 队员信号，准备要破墙

    SUGGEST_TO_BREAK_OVERLAP         = 15  # 团队信号，建议马上打破重叠
    READY_TO_BREAK_OVERLAP           = 16  # 队员信号，准备要主动打破重叠

    FORCED_MARCH                     = 17  # 团队信号，强制行军
    READY_TO_FORCED_MARCH            = 18  # 队员信号，准备强制行军

    SHOULD_LEAVE_TEAMMATE            = 19  # 团队信号，需要和队友打破重叠
    READY_TO_LEAVE_TEAMMATE          = 20  # 队员信号，准备和队友打破重叠

    SUGGEST_TO_BACK_AWAY_FROM_BRICK  = 21  # 团队信号，建议反向远离墙壁
    READY_TO_BACK_AWAY_FROM_BRICK    = 22  # 队员信号，准备反向远离墙壁


    @staticmethod
    def is_break(signal):
        """
        该信号是否意味着沟通停止
        也就是是否为未处理或无法处理

        """
        return signal in (

                __class__.INVALID,
                __class__.UNHANDLED,
                __class__.CANHANDLED,

                )

#{ END }#