# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:04:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 04:08:05

#{ BEGIN }#
import random
#{ END }#
import numpy as np
from core.botzone import Tank2Botzone
from core.action import Action
from core.field import WaterField
from core.map_ import Tank2Map
from core.const import MAP_WIDTH, MAP_HEIGHT, TANKS_PER_SIDE, LONG_RUNNING_MODE
from core.stream import BotzoneIstream, BotzoneOstream
from core.strategy import MoveToWaterStrategy

#{ BEGIN }#

if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_, long_running=LONG_RUNNING_MODE)

    istream = BotzoneIstream()
    ostream = BotzoneOstream()

    _dx = Action.DIRECTION_OF_ACTION_X
    _dy = Action.DIRECTION_OF_ACTION_Y

    while True:

        if LONG_RUNNING_MODE: # 这个模式下 map 对象会复用，首先需要重置
            map_.reset()

        terminal.handle_input(stream=istream)

        side = terminal.mySide
        tanks = map_.tanks[side]

        waterPoints = MoveToWaterStrategy.find_water_points(map_)

        actions = []
        for tank in tanks:
            '''availableActions = [
                action for action in range(Action.STAY, Action.SHOOT_LEFT + 1)
                    if map_.is_valid_action(tank, action)
            ]
            actions.append(random.choice(availableActions))'''
            s = MoveToWaterStrategy(tank, map_, waterPoints)
            action = s.make_decision()

            if not map_.is_valid_action(tank, action): # 说明是墙或水
                x, y = tank.xy
                x += _dx[action]
                y += _dy[action]
                fields = map_.get_fields(x, y)
                assert len(fields) > 0, "no fields in (%s, %s)" % (x, y)
                field = fields[0]
                if not isinstance(field, WaterField): # 说明是墙
                    action += 4 # 射击，这个 action 一定成功，因为若上回合射击，这回合必定不会碰到墙
                else: # 是水面
                    if not Action.is_shoot(tank.previousAction): # 上回合未射击
                        action += 4
                    else: # 上回合射击
                        action = Action.STAY # 如果游戏正常，则会停下，否则一开始会认为是合法，并继续移动

            actions.append(action)

        terminal.make_output(actions, stream=ostream)


#{ END }#