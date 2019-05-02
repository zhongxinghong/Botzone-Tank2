# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-01 18:00:49
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-02 11:29:32
"""
当前状态

用于被队友主动获取

"""

__all__ = [

    "Status",

    ]

from ..utils import UniqueIntEnumMeta, debug_print, debug_pprint

#{ BEGIN }#

class Status(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 100

    NONE       = 0  # 空状态

    AGGRESSIVE = 1  # 侵略性的
    DEFENSIVE  = 2  # 防御性的
    STALEMENT  = 3  # 僵持的
    DYING      = 4  # 准备要挂了
    DIED       = 5  # 已经挂了

    REALODING  = 9  # 正在装弹，下回合无法射击

    ENCOUNT_ENEMY     = 11
    ENCOUNT_ONE_ENEMY = 12
    ENCOUNT_TWO_ENEMY = 12

    KEEP_ON_MARCHING     = 21  # 继续行军
    READY_TO_ATTACK_BASE = 22  # 准备拆基地
    READY_TO_FIGHT_BACK  = 23  # 准备反击
    READY_TO_DODGE       = 24  # 准备闪避敌人
    READY_TO_KILL_ENEMY  = 25  # 准备击杀敌人
    READY_TO_BLOCK_ROAD  = 26  # 准备堵路
    KEEP_ON_OVERLAPPING  = 27  # 等待与自己重叠的敌人的决策
    WAIT_FOR_MARCHING    = 28  # 存在风险，等待进攻
    HUNTING_ENEMY        = 29  # 主动追杀敌军

    ANTICIPATE_TO_KILL_ENEMY = 30 # 主动防御时，尝试击杀敌军，这个状态可以用来记忆行为
    BLOCK_ROAD_FOR_OUR_BASE  = 31 # 主动防御时，遇到敌方面向基地，但没有炮弹，自己又恰好能阻挡在中间
    SACRIFICE_FOR_OUR_BASE   = 32 # 主动防御时，遇到敌方下一炮打掉基地，自己又恰好能阻挡

    READY_TO_BREAK_BRICK = 40  # 准备破墙，对应 Status.BREAK_BRICK


    DEADLOCK_WITH_BLUE_0_AGAINST_BRICK = 41  # 和蓝方 0 号坦克隔墙僵持
    DEADLOCK_WITH_BLUE_1_AGAINST_BRICK = 42  # 和蓝方 1 号坦克隔墙僵持
    DEADLOCK_WITH_RED_0_AGAINST_BRICK  = 43  # 和红方 0 号坦克隔墙僵持
    DEADLOCK_WITH_RED_1_AGAINST_BRICK  = 44  # 和红方 1 号坦克隔墙僵持


    __Status_Name_Cache = None

    @staticmethod
    def get_name(status):
        """
        通过状态值自动判定方法
        """
        if __class__.__Status_Name_Cache is None:
            cache = __class__.__Status_Name_Cache = {}
            for k, v in __class__.__dict__.items():
                if not k.startswith("__"):
                    if isinstance(v, int):
                        key = k.title()
                        cache[v] = key
        cache = __class__.__Status_Name_Cache
        return cache.get(status, None) # 应该保证一定有方法？

#{ END }#