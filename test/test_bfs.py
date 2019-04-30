# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-04-29 07:33:08
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-29 22:01:22
"""
[TEST] BFS 搜索行为

测试特殊情况
--------------
1. 无法到达的目标
2. 无法摧毁的目标
3. 原地


经验之谈
------------
1. 一开始决策的时候，因为对方的 tank 处在底线，相当于距离加 2 ，但是游戏进行之后，
对方的 tank 移开，一开始决策最短的距离，并不一定是游戏过程中最短的，因此一开始的
时候需要将对方 tank 当做不存在


"""


import os
import json
import numpy as np
from pprint import pprint
from _utils import to_stream, json_load, cut_by_turn

import sys
sys.path.append("../")

from core.const import MAP_WIDTH, MAP_HEIGHT
from core.field import Field, BaseField, BrickField, EmptyField, SteelField, WaterField, TankField
from core.map_ import Tank2Map
from core.botzone import Tank2Botzone
from core.strategy._utils import find_shortest_route_for_move, find_shortest_route_for_shoot,\
    get_route_length, DEFAULT_BLOCK_TYPES, DEFAULT_DESTROYABLE_TYPES


DATA_DIR = "../dataset/5cc5632075e55951524b9c77/"

BLUE_INPUT_JSON = os.path.join(DATA_DIR, "blue.input.json")
RED_INPUT_JSON  = os.path.join(DATA_DIR, "red.input.json")

blueInputJSON = json_load(BLUE_INPUT_JSON)
redInputJSON  = json_load(RED_INPUT_JSON)


CENTER_STEEL_XY = (4, 4)
BLUE_BASE_XY    = (4, 0)
RED_BASE_XY     = (4, 8)

BLUE_TANK_0_INIT_XY = (2, 0)
BLUE_TANK_1_INIT_XY = (6, 0)
RED_TANK_0_INIT_XY  = (6, 8)
RED_TANK_1_INIT_XY  = (2, 8)


if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_, long_running=False)

    inputJSON = cut_by_turn(redInputJSON, turn=1)

    stream = to_stream(json.dumps(inputJSON))

    terminal.handle_input(stream=stream)


    for tanks in map_.tanks:
        for tank in tanks:

            side = tank.side
            oppSide = 1 - side
            selfBase = map_.bases[side]
            oppBase = map_.bases[oppSide]

            cMatrixMap = map_.matrix_T.copy()

            for oppTank in map_.tanks[oppSide]:
                cMatrixMap[oppTank.xy] = Field.EMPTY # 先将对方 tank 设为空！

            print("map without enemies:\n", cMatrixMap.T)

            route1 = find_shortest_route_for_move(
                        tank.xy,
                        oppBase.xy,
                        cMatrixMap,
                        block_types=DEFAULT_BLOCK_TYPES+(
                            Field.BASE + 1 + side,
                            Field.TANK + 1 + side,
                            Field.MULTI_TANK,
                        ))

            route2 = find_shortest_route_for_shoot(
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
                            Field.TANK + 1 + oppSide, # 对方坦克
                            #Field.MULTI_TANK,
                        ))


            map_.debug_print_out(compact=True)
            print(route1, get_route_length(route1))
            print(route2, get_route_length(route2))
