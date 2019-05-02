# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 22:14:37
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 23:52:51
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
    UNHANDLED   = 1   # 未处理团队信号
    CANHANDLED  = 2   # 未能处理团队信号

    BREAK_BRICK = 10  # 破墙

#{ END }#