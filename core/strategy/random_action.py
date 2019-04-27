# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:22:10
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 19:18:48
"""
[TEST] 随机行为

- 确保行为是合理的
- 不会摧毁己方基地
- 只考虑自己行为的情况下，不会摧毁己方坦克
    - 例外： 己方坦克与地方坦克重合时
    - 例外： 己方坦克下回合移动到被攻击的路径上时
"""

__all__ = [

    "RandomActionStrategy",

    ]

from ..global_ import random
from ..utils import debug_print
from ..action import Action
from ..field import BaseField, TankField
from .abstract import Strategy

#{ BEGIN }#

class RandomActionStrategy(Strategy):

    def make_decision(self):

        tank = self._tank
        map_ = self._map
        # debug_print("RandomAction decision, tank %s" % tank)

        availableActions = []

        for action in range(Action.STAY, Action.SHOOT_LEFT + 1):

            if not map_.is_valid_action(tank, action):
                continue
            elif Action.is_shoot(action):
                destroyedFields = map_.get_destroyed_fields(tank, action)
                # debug_print("Destroyed Fields:", destroyedFields)
                if len(destroyedFields) == 1:
                    field = destroyedFields[0]
                    if isinstance(field, BaseField) and field.side == tank.side:
                        continue
                    elif isinstance(field, TankField) and field.side == tank.side:
                        continue

            availableActions.append(action)

        # debug_print("Available actions: %s\n" % availableActions)
        return random.choice(availableActions)

#{ END }#