# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-04-29 01:51:56
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-04-29 06:27:16

import os
import json
from pprint import pprint
from _utils import to_stream, json_load, cut_by_turn

import sys
sys.path.append("../")

from core.botzone import Tank2Botzone
from core.map_ import Tank2Map
from core.const import MAP_WIDTH, MAP_HEIGHT


DATA_DIR = "../dataset/5cc5a74b75e55951524bc636/"

BLUE_INPUT_JSON = os.path.join(DATA_DIR, "blue.input.json")
RED_INPUT_JSON  = os.path.join(DATA_DIR, "red.input.json")

blueInputJSON = json_load(BLUE_INPUT_JSON)
redInputJSON  = json_load(RED_INPUT_JSON)



if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_, long_running=False)

    inputJSON = cut_by_turn(redInputJSON, turn=-1)

    stream = to_stream(json.dumps(inputJSON))

    terminal.handle_input(stream=stream)

    map_.debug_print_out()
    for _ in range(9):
        map_.revert()
