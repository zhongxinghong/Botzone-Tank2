# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 04:38:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 08:16:38

import os
import json
from pprint import pprint
from copy import deepcopy
from _utils import to_stream, json_load

import sys
sys.path.append("../")

from core.botzone import Tank2Botzone
from core.map_ import Tank2Map
from core.const import MAP_WIDTH, MAP_HEIGHT
from core.action import Action
from core.strategy import MoveToWaterStrategy, RandomActionStrategy, MarchIntoEnemyBaseStrategy,\
                        SkirmishStrategy


DATA_DIR = "../dataset/5cc4ec5675e55951524b45a3/"

BLUE_INPUT_JSON = os.path.join(DATA_DIR, "blue.input.json")
RED_INPUT_JSON  = os.path.join(DATA_DIR, "red.input.json")

blueInputJSON = json_load(BLUE_INPUT_JSON)
redInputJSON  = json_load(RED_INPUT_JSON)


def cut_by_turn(inputJSON, turn=-1):
    """
    截短 json 数据

    使得最后一回合为第 turn 回合
    """
    if turn <= 0:
        return inputJSON

    maxTurn = len(inputJSON["responses"]) + 1 # 从 1 开始算起的 turn
    if turn > maxTurn:
        raise Exception("no such turn %s" % turn)

    res = deepcopy(inputJSON)
    res["requests"] = inputJSON["requests"][:turn-1+1] # 包含 header
    res["responses"] = inputJSON["responses"][:turn-1]

    return res


if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_)

    inputJSON = cut_by_turn(redInputJSON, turn=5)

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