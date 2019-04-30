# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 04:38:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 01:38:45

import os
import json
from pprint import pprint
from _utils import to_stream, json_load, cut_by_turn

import sys
sys.path.append("../")

from core.botzone import Tank2Botzone
from core.map_ import Tank2Map
from core.const import MAP_WIDTH, MAP_HEIGHT
from core.action import Action
from core.strategy import  MarchIntoEnemyBaseStrategy, SkirmishStrategy


DATA_DIR = "../dataset/5cc72a4b75e55951524cbc25/"

BLUE_INPUT_JSON = os.path.join(DATA_DIR, "blue.input.json")
RED_INPUT_JSON  = os.path.join(DATA_DIR, "red.input.json")

blueInputJSON = json_load(BLUE_INPUT_JSON)
redInputJSON  = json_load(RED_INPUT_JSON)



if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_)

    inputJSON = cut_by_turn(blueInputJSON, turn=5)

    stream = to_stream(json.dumps(inputJSON))

    terminal.handle_input(stream=stream)

    actions = []
    for tanks in map_.tanks:
        for tank in tanks:

            if tank.destroyed:
                actions.append(Action.STAY)
                continue

            action = Action.INVALID

            for _Strategy in [SkirmishStrategy]:
                s = _Strategy(tank, map_)
                action = s.make_decision()
                print("%r, %s" % (tank, action) )
                if action != Action.INVALID:
                    break

            if action == Action.INVALID: # 没有任何一种策略适用，则原地等待
                action = Action.STAY

            actions.append(action)