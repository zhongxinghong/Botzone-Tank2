# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-01 18:00:49
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 03:24:25
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

    RELOADING  = 9  # 正在装弹，下回合无法射击

    ENCOUNT_ENEMY      = 11
    ENCOUNT_ONE_ENEMY  = 12
    ENCOUNT_TWO_ENEMY  = 13
    OVERLAP_WITH_ENEMY = 14

    KEEP_ON_MARCHING             = 21  # 继续行军
    READY_TO_ATTACK_BASE         = 22  # 准备拆基地
    READY_TO_FIGHT_BACK          = 23  # 准备反击
    READY_TO_DODGE               = 24  # 准备闪避敌人
    READY_TO_KILL_ENEMY          = 25  # 准备击杀敌人
    READY_TO_BLOCK_ROAD          = 26  # 准备堵路
    KEEP_ON_OVERLAPPING          = 27  # 等待与自己重叠的敌人的决策
    WAIT_FOR_MARCHING            = 28  # 存在风险，等待进攻
    HAS_ENEMY_BEHIND_BRICK       = 29  # 隔墙有人
    PREVENT_BEING_KILLED         = 30  # 为了防止被射击而停下
    HUNTING_ENEMY                = 31  # 主动追杀敌军
    ACTIVE_DEFENSIVE             = 32  # 主动防御状态
    WILL_DODGE_TO_LONG_WAY       = 33  # 遭遇敌人自己没有炮弹，为了保命而闪避，但是增加了攻击路线长度
    OPPOSITE_SHOOTING_WITH_ENEMY = 34  # 正在和敌人对射
    READY_TO_BACK_AWAY           = 35  # 假装逃跑
    READY_TO_CLEAR_A_ROAD_FIRST  = 36  # 进攻时预先清除与自己相隔一步的土墙
    READY_TO_DOUBLE_KILL_ENEMIES = 37  # 遇到敌人重叠在一起，尝试和两个敌人同归于尽
    READY_TO_LEAVE_TEAMMATE      = 38  # 准备和队友打破重叠
    FACING_TO_ENEMY_BASE         = 39  # 正面敌人基地，或者和敌人基地处在同一直线上
    READY_TO_FOLLOW_ENEMY        = 40  # 准备跟随墙后敌人的移动方向

    READY_TO_PREPARE_FOR_BREAK_BRICK = 51 # 准备为破墙而准备闪避路线
    READY_TO_BREAK_BRICK             = 52 # 准备破墙
    READY_TO_BREAK_OVERLAP           = 53 # 准备主动打破重叠
    READY_TO_FORCED_MARCH            = 54 # 准备主动强攻

    ATTEMPT_TO_KILL_ENEMY   = 60 # 主动防御时，尝试击杀敌军，这个状态可以用来记忆行为
    BLOCK_ROAD_FOR_OUR_BASE = 61 # 主动防御时，遇到敌方面向基地，但没有炮弹，自己又恰好能阻挡在中间
    SACRIFICE_FOR_OUR_BASE  = 62 # 主动防御时，遇到敌方下一炮打掉基地，自己又恰好能阻挡


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