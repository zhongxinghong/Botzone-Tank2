# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:18:33
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 10:21:50
"""
游戏策略

封装各种策略，每个具体的策略类会根据给定的 tank 和 map 以及其他一些参数
给出下一个行为的决策

每个具体定义的策略类必须实现 abstract.py 中的抽象接口
"""

__all__ = [

    "RandomActionStrategy",
    "MoveToWaterStrategy",
    "MarchIntoEnemyBaseStrategy",
    "SkirmishStrategy",
    "EarlyWarningStrategy",

    ]

from .random_action import RandomActionStrategy
from .move_to_water import MoveToWaterStrategy
from .march_into_enemy_base import MarchIntoEnemyBaseStrategy
from .skirmish import SkirmishStrategy
from .early_warning import EarlyWarningStrategy