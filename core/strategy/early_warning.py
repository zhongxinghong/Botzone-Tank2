# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 06:49:24
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 01:46:18
"""
预警策略

处理下面的情况：
- 自己开一炮后，下一回合可能被对方打死
- 自己移动一步后，下一回合可能被对方打死（目前尚未实现）

优先级高于遭遇战策略，如果发现当前已经为遭遇战，则留给遭遇战策略决策

"""

__all__ = [

    "EarlyWarningStrategy",

    ]

from ..const import DIRECTIONS_URDL
from ..global_ import np
from ..utils import debug_print
from ..action import Action
from ..field import EmptyField, WaterField, TankField, BaseField, BrickField, SteelField
from ._utils import get_destroyed_fields
from .abstract import SingleTankStrategy
from .march_into_enemy_base import MarchIntoEnemyBaseStrategy
from .skirmish import SkirmishStrategy

#{ BEGIN }#

class EarlyWarningStrategy(SingleTankStrategy):

    def make_decision(self):

        tank = self._tank
        map_ = self._map
        oppSide = 1 - tank.side

        _dx = Action.DIRECTION_OF_ACTION_X
        _dy = Action.DIRECTION_OF_ACTION_Y

        # 缓存决策行为
        _actionDecidedBySkirmishStrategy = None
        _actionDecidedByMarchIntoEnemyBaseStrategy = None


        ## 检查四个方向是否存在一堵墙加地方坦克的情况 ##

        def _is_dangerous_action(preAction, riskMoveActionByDxDy):
            """
            危险行为被定义为，下一回合按照预期行为执行，会引发危险

            只有在下一回合射击，且射击方向与风险方向相同时，才会引发危险

            Input:
                - preAction               int   准备要发生的行为
                - riskMoveActionByDxDy    int   已经预先知道有风险的方向对应的 move-action
            """
            if Action.is_shoot(preAction) and (preAction - 4 == riskMoveActionByDxDy):
                # 下回合射击方向为引发危险的方向
                destroyedFields = get_destroyed_fields(tank, preAction, map_)
                if len(destroyedFields) > 0:
                    for field in destroyedFields:
                        if isinstance(field, BrickField): # 有墙被摧毁，会引发危险
                            return True
            return False # 其余情况下不算危险行为


        for idx, (dx, dy) in enumerate(DIRECTIONS_URDL):

            x, y = tank.xy
            foundBrick = False # 这个方向上是否找到墙

            foundRisk = False
            riskDxDy = (0, 0)
            oppTank = None

            while True:
                x += dx
                y += dy
                if not map_.in_map(x, y):
                    break
                currentFields = map_[x, y]
                if len(currentFields) == 0:
                    continue
                elif len(currentFields) > 1:
                    if not foundBrick: # 遭遇战
                        return Action.INVALID
                    else: # 墙后有地方坦克
                        for field in currentFields:
                            if isinstance(field, TankField) and field.side == oppSide:
                                oppTank = field
                                break
                        else:
                            raise Exception("???")
                        foundRisk = True
                        reskDxDy = (dx, dy)
                        break
                else: # 遇到 基地/墙/水/钢墙/坦克
                    field = currentFields[0]
                    if isinstance(field, (EmptyField, WaterField) ):
                        continue
                    elif isinstance(field, SteelField): # 钢墙打不掉，这个方向安全
                        break
                    elif isinstance(field, BaseField): # 遇到基地，不必预警 ...
                        return Action.INVALID # 应该直接打掉 ... # TODO: 如果有炮弹
                    elif isinstance(field, BrickField):
                        if not foundBrick: # 第一次找到墙，标记，并继续往后找
                            foundBrick = True
                            continue
                        else:
                            break # 连续两道墙。很安全
                    elif isinstance(field, TankField) and field.side == oppSide:
                        if not foundBrick: # 遭遇战
                            return Action.INVALID
                        else: # 墙后有坦克
                            foundRisk = True
                            reskDxDy = (dx, dy)
                            oppTank = field
                            break
                    else: # 遇到队友，不必预警
                        # TODO: 其实不一定，因为队友可以离开 ...
                        break

            if foundRisk: # 发现危险，判断在下一回合按照预期行为是否会引发危险

                if _actionDecidedBySkirmishStrategy is None:
                    s = SkirmishStrategy(tank, map_)
                    _actionDecidedBySkirmishStrategy = s.make_decision()

                if _actionDecidedByMarchIntoEnemyBaseStrategy is None:
                    s = MarchIntoEnemyBaseStrategy(tank, map_)
                    _actionDecidedByMarchIntoEnemyBaseStrategy = s.make_decision()

                _action1 = _actionDecidedBySkirmishStrategy
                _action2 = _actionDecidedByMarchIntoEnemyBaseStrategy

                _riskMoveActionByDxDy = idx

                for _action in [_action1, _action2]:
                    if Action.is_valid(_action):
                        if _is_dangerous_action(_action, _riskMoveActionByDxDy):
                            # 必须在预警策略中决策，而且必须在存在危险行为时决策
                            # ----------------------------------------------
                            # 如果跳过这个危险，去判断其他方向：
                            # 1. 如果其他方向也有危险，再做出这个决策，不过是延迟行为。
                            # 2. 如果其他方向均没有危险，预警策略就会交给低优先级策略决策
                            # 由于此处已经知道低优先级策略存在危险，因此相当于预警策略
                            # 做出了错误的决定。
                            # ----------------------------------------------
                            # 因此必须要在此处立即做出决策
                            #
                            # TODO: 是否有比 STAY 更好的方案
                            return Action.STAY

            # 预期的行为均不会造成危险，或者没有发现有风险行为，则继续循环
            pass
        # endfor #

        ## 检查下一步行动后，是否有可能遇到风险 ##

        if _actionDecidedBySkirmishStrategy is None:
            s = SkirmishStrategy(tank, map_)
            _actionDecidedBySkirmishStrategy = s.make_decision()

        if _actionDecidedByMarchIntoEnemyBaseStrategy is None:
            s = MarchIntoEnemyBaseStrategy(tank, map_)
            _actionDecidedByMarchIntoEnemyBaseStrategy = s.make_decision()

        _action1 = _actionDecidedBySkirmishStrategy
        _action2 = _actionDecidedByMarchIntoEnemyBaseStrategy

        for _action in [_action1, _action2]:
            if Action.is_valid(_action):

                foundRisk = False

                if Action.is_move(_action):
                    # 移动后恰好位于敌方射击方向，然后被打掉
                    x, y = tank.xy
                    x2 = x + _dx[_action]
                    y2 = y + _dy[_action]

                    for idx, (dx, dy) in enumerate(DIRECTIONS_URDL):

                        if np.abs(idx - _action) == 2:
                            continue # 不可能在移动方向的反向出现敌人

                        x, y = x2, y2
                        while True:
                            x += dx
                            y += dy
                            if not map_.in_map(x, y):
                                break
                            currentFields = map_[x, y]
                            if len(currentFields) == 0:
                                continue
                            elif len(currentFields) > 1: # 存在敌方 tank ，有风险
                                foundRisk = True
                                break
                            else: # 遇到/墙/水/钢墙/坦克
                                field = currentFields[0]
                                if isinstance(field, (EmptyField, WaterField) ):
                                    continue
                                elif (  isinstance(field, TankField)
                                        and field.side == oppSide
                                        and not Action.is_shoot(field.previousAction)
                                    ): # 当且仅当发现有炮弹的地方坦克时，判定为危险
                                    foundRisk = True
                                else: # 其他任何情况均没有危险
                                    break
                            if foundRisk:
                                break
                        if foundRisk:
                            break

                elif Action.is_shoot(_action):
                    # 射击后击破砖块，但是敌方从两旁出现，这种情况可能造成危险
                    destroyedFields = get_destroyed_fields(tank, _action, map_)
                    if len(destroyedFields) == 0:
                        pass # 没有危险
                    elif len(destroyedFields) > 1: # 不可能出现这种情况，因为这算遭遇战
                        return Action.INVALID
                    else: # len(destroyedFields) == 1:
                        field = destroyedFields[0]
                        if isinstance(field, BrickField): # 击中砖块，会造成危险
                            # 现在需要判断砖块之后的道路两侧是否有敌人
                            x, y = field.xy
                            _action -= 4
                            while True:
                                x += _dx[_action]
                                y += _dy[_action]
                                if not map_.in_map(x, y):
                                    break
                                currentFields = map_[x, y]
                                # 由于之前的判定，此处理论上不会遇到敌方 tank
                                if len(currentFields) > 1:
                                    return Action.INVALID # 理论上不会遇到
                                if len(currentFields) == 1:
                                    _field = currentFields[0]
                                    if isinstance(_field, (WaterField, SteelField, BrickField) ):
                                        break # 发现了敌人无法在下一步移动到的kuai，因此即使敌人在周围也是安全的

                                # 判断周围的方块是否有地方坦克
                                if len(currentFields) == 0:
                                    x3, y3 = x, y
                                elif len(currentFields) == 1:
                                    x3, y3 = currentFields[0].xy

                                for idx, (dx, dy) in enumerate(DIRECTIONS_URDL):
                                    if idx % 2 == _action % 2: # 同一直线
                                        continue
                                    x4 = x3 + dx
                                    y4 = y3 + dy
                                    if not map_.in_map(x4, y4):
                                        continue
                                    for _field in map_[x4, y4]:
                                        debug_print(_field)
                                        if (isinstance(_field, TankField)
                                            and _field.side == oppSide
                                            ): # 当道路两旁存在敌人坦克时，认为有风险
                                            foundRisk = True
                                            break
                                    if foundRisk:
                                        break
                                if foundRisk:
                                    break
                            # endwhile #
                        # endif #

                else: # 不是移动行为也不是设计行为，但是合理，因此是静止行为
                    pass # 静止行为不会有风险

                if foundRisk: # 遇到风险，等待
                    # TODO: 也许还有比等待更好的方法
                    return Action.STAY

            # endif #
        # endfor #

        return Action.INVALID # 都不存在风险，预警策略不适用

#{ END }#