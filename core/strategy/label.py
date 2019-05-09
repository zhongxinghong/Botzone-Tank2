# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-04 02:24:15
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-09 18:16:29
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

    BREAK_OVERLAP_SIMULTANEOUSLY = 1   # 会和我同时打破重叠


#{ END }#
