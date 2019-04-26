# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 04:38:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 04:33:10

import os
import json
from pprint import pprint
from utils import to_stream, json_load

import sys
sys.path.append("../")

from core.botzone import Tank2Botzone
from core.map_ import Tank2Map
from core.const import MAP_WIDTH, MAP_HEIGHT
from core.strategy import MoveToWaterStrategy


DATA_DIR = "../dataset/5cc3696e35f461309c2a7581/"

BLUE_INPUT_JSON = os.path.join(DATA_DIR, "blue.input.json")
RED_INPUT_JSON  = os.path.join(DATA_DIR, "red.input.json")

blueInputJSON = json_load(BLUE_INPUT_JSON)
redInputJSON  = json_load(RED_INPUT_JSON)


if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_)

    stream = to_stream(json.dumps(redInputJSON))

    terminal.handle_input(stream=stream)

    waterPoints = MoveToWaterStrategy.find_water_points(map_)

    tanks = map_.tanks[terminal.mySide]

    for tank in tanks:
        s = MoveToWaterStrategy(tank, map_, waterPoints)
        res = s.make_decision()
        print(res)