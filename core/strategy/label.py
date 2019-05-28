# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-04 02:24:15
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 03:01:12
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
    KEEP_ON_WITHDRAWING                   = 4  # 我方坦克持久化撤退状态
    DONT_WITHDRAW                         = 5  # 强制性要求一个队员不再防御
    ALWAYS_BACK_AWAY                      = 6  # 我方坦克总是尝试回头


    __Status_Name_Cache = None

    @staticmethod
    def get_name(status):
        """
        通过状态值自动判定方法
        """
        if __class__.__Status_Name_Cache is None:
            cache = __class__.__Status_Name_Cache = {}
            for k, v in __class__.__dict__.items():
                if not k.startswith("_"):
                    if isinstance(v, int):
                        key = k.title()
                        cache[v] = key
        cache = __class__.__Status_Name_Cache
        return cache.get(status, None) # 应该保证一定有方法？

#{ END }#
