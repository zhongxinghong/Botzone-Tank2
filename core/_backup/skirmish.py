# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 04:48:30
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 12:34:27
"""
与敌方 tank 遭遇，下回合可能会被打死的情况下，单架坦克进行决策

Step:
- 如果与敌方坦克重叠
    1. 如果对方有炮，则危险，保全自己起见则等待
    2. 如果对方没有跑，则安全，放弃这个策略
- 如果上下左右四路中有敌人
    1. 如果自己有炮，则朝他开火
    2. 如果自己没跑，但是对方有炮，则尝试闪避
"""

__all__ = [

    "SkirmishStrategy",

    ]

from ..const import DIRECTIONS_URDL
from ..utils import debug_print
from ..action import Action
from ..field import TankField, WaterField, EmptyField
from .abstract import SingleTankStrategy

#{ BEGIn }#

class SkirmishStrategy(SingleTankStrategy):

    def make_decision(self):

        tank = self._tank
        map_ = self._map
        oppSide = 1 - tank.side

        ## 如果与敌方重叠 ##
        onSiteFields = map_[tank.xy]
        if len(onSiteFields) > 1:
            for field in onSiteFields: #　field 必定是 TankField
                assert isinstance(field, TankField), "unexpected field %r" % field
                if field.side == tank.side: # 是自己或者队友
                    continue
                else:
                    oppTank = field
                    if Action.is_shoot(oppTank.previousAction):
                        return Action.INVALID # 敌方上回合射击，说明下回合是安全的
                    else:
                        # TODO: 但是等待有可能让别人直接跑走，是否可以考虑回头打？
                        return Action.STAY # 敌人这回合可以开炮，等待是最安全的做法


        shouldShoot = False
        shouldShootDxDy = (0, 0) # 记录应该往哪个方向射击
        oppTank = None

        ## 考虑四周是否有敌军 ##
        for dx, dy in DIRECTIONS_URDL:
            if shouldShoot: # 已经发现需要射击的情况
                break
            x, y = tank.xy
            while True:
                x += dx
                y += dy
                if not map_.in_map(x, y):
                    break
                currentFields = map_[x, y]
                if len(currentFields) == 0: # 没有对象
                    continue
                elif len(currentFields) > 1: # 多辆坦克，准备射击
                    # TODO: 是否应该射掉队友？
                    for field in currentFields:
                        assert isinstance(field, TankField), "unexpected field %r" % field
                        if field.side == oppSide:
                            oppTank = field
                            break
                    else:
                        raise Exception("???") # 这种情况不应该出现
                    shouldShoot = True
                    shouldShootDxDy = (dx, dy)
                    break
                else: # len == 1
                    field = currentFields[0]
                    if isinstance(field, (EmptyField, WaterField) ):
                        continue
                    elif not isinstance(field, TankField): # 说明这个方向上没有敌人
                        break
                    elif field.side != tank.side: # 遇到了敌人，准备射击
                        oppTank = field
                        shouldShoot = True
                        shouldShootDxDy = (dx, dy)
                        break
                    else: # 遇到了队友 ...
                        break # 继续判断其他方向是否有敌军

        ## 尝试射击 ##
        if shouldShoot:
            x, y = tank.xy
            dx, dy = shouldShootDxDy
            action = Action.get_action(x, y, x+dx, y+dy) + 4  # 通过 move-action 间接得到 shoot-action
            if map_.is_valid_shoot_action(tank, action):
                return action # 可以射击
            else: # 不能射击 ...
                if not Action.is_shoot(oppTank.previousAction): #　并且敌方有炮弹
                    # 尝试闪避
                    _ineffectiveAction = action - 4 # 闪避后应当尝试离开射击方向所在直线，否则是无效的
                    for _action in range(Action.MOVE_UP, Action.MOVE_LEFT + 1):
                        if _action % 2 == _ineffectiveAction % 2:
                            continue # 与无效移动行为方向相同，不能采用
                        elif map_.is_valid_move_action(tank, _action):
                            # TODO: 闪避方向是否还可以选择？
                            return _action # 返回遇到的第一个可以用来闪避的移动行为

        return Action.INVALID # 该策略不适用

#{ END }#