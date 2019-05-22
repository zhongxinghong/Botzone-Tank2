# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-04 02:24:15
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-22 19:21:12
"""
标记类

学习一些敌人的特征，给特定的敌人添加标记
从而动态改变自己的行为

"""

__all__ = [

    "Label"

    ]

from ..utils import UniqueIntEnumMeta

#{ BEGIN }#

class Label(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 300

    NONE = 0

    BREAK_OVERLAP_SIMULTANEOUSLY          = 1  # 会和我同时打破重叠
    SIMULTANEOUSLY_SHOOT_TO_BREAK_OVERLAP = 2  # 回合我方同时以射击的方式打破重叠
    IMMEDIATELY_BREAK_OVERLAP_BY_MOVE     = 3  # 当敌人和我方坦克重叠时，对方立即与我打破重叠

#{ END }#
