# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 03:31:43
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 04:33:13
"""
不顾一切冲向敌方基地

Step:
1. 通过 BFS 查找到达对方基地的最近路径
2. 优先移动
3. 如果遇到路障，则射击（遇到队友除外）
4. 如果不能射击，则原地等待
"""

__all__ = [

    "MarchIntoEnemyBaseStrategy",

    ]

from ..const import DEBUG_MODE
from ..global_ import pprint
from ..utils import debug_print
from ..action import Action
from ..field import Field, TankField, SteelField, BaseField
from ._utils import get_destroyed_fields
from ._bfs import find_shortest_route_for_shoot, DEFAULT_BLOCK_TYPES, DEFAULT_DESTROYABLE_TYPES
from .abstract import SingleTankStrategy

#{ BEGIN }#

class MarchIntoEnemyBaseStrategy(SingleTankStrategy):

    def make_decision(self):

        tank = self._tank
        map_ = self._map
        matrix_T = map_.matrix_T

        _dx = Action.DIRECTION_OF_ACTION_X
        _dy = Action.DIRECTION_OF_ACTION_Y

        side    = tank.side
        oppSide = 1 - tank.side
        oppBase = map_.bases[oppSide]

        cMatrixMap = matrix_T.copy() # 模拟一个没有敌人 tank 的地图

        debug_print("cMatrixMap:\n", cMatrixMap)

        debug_print(map_.tanks)
        for oppTank in map_.tanks[oppSide]:
            if cMatrixMap[x, y] == Field.TANK + 1 + oppTank.side:
                cMatrixMap[oppTank.xy] = Field.EMPTY # 先将对方 tank 设为空！

        debug_print("cMatrixMap:\n", cMatrixMap)

        route = find_shortest_route_for_shoot(
                    tank.xy,
                    oppBase.xy,
                    cMatrixMap,
                    block_types=DEFAULT_BLOCK_TYPES+(
                        Field.BASE + 1 + side,    # 己方基地
                        Field.TANK + 1 + side,    #　己方坦克
                        Field.MULTI_TANK,         # 多重坦克，不能移动
                    ),
                    destroyable_types=DEFAULT_DESTROYABLE_TYPES+(
                        Field.BASE + 1 + oppSide, # 对方基地
                        #Field.TANK + 1 + oppSide, # 对方坦克
                        #Field.MULTI_TANK,
                    ))

        if len(route) == 0: # 没有找到路线，这种情况不可能
            return Action.STAY

        if len(route) == 1:    # 说明 start 和 end 相同
            return Action.STAY # 停留不动

        x1, y1 = tank.xy
        x3, y3, _, _ = route[1] # 跳过 start
        action = Action.get_action(x1, y1, x3, y3)

        ## 优先移动 ##
        if map_.is_valid_move_action(tank, action):

            # 但是，如果正前方就是基地，则不移动，只射击
            hasEnemyBaseInFront = False
            x, y = tank.xy
            while True:
                x += _dx[action]
                y += _dy[action]
                if not map_.in_map(x, y):
                    break
                currentFields = map_[x, y]

                foundSteelField = False
                for field in currentFields:
                    if isinstance(field, SteelField):
                        foundSteelField = True
                        break
                    elif field is oppBase: # 是敌方
                        hasEnemyBaseInFront = True
                        break
                    else: # 继续寻找
                        continue
                if foundSteelField: # 钢墙不能击穿，因此该方向不在往下找
                    break

            if hasEnemyBaseInFront: # 地方基地在前方，且没有钢墙阻拦
                if map_.is_valid_shoot_action(tank, action + 4): # 如果自己可以射击
                    action += 4
                    destroyedFields = get_destroyed_fields(tank, action, map_)
                    for field in destroyedFields: # 为了防止射到队友
                        if isinstance(field, TankField) and field.side == tank.side:
                            return Action.STAY # 原地不动
                    return action # 否则射击
                else:
                    return Action.STAY # 不能射击，则等待
            return action # 否则，正常移动


        ## 遇到墙/敌方基地/坦克 ##
        action += 4 # 尝试射击
        if map_.is_valid_shoot_action(tank, action):
            destroyedFields = get_destroyed_fields(tank, action, map_)
            # 仅仅需要防止射到自己队友
            if len(destroyedFields) == 1:
                field = destroyedFields[0]
                if isinstance(field, TankField) and field.side == tank.side:
                    # TODO: 这种情况下可能会出现两架坦克互相等待的情况？
                    return Action.STAY
            return action # 到此说明可以射击

        return Action.STAY # 不能射击，只好等待

#{ END }#