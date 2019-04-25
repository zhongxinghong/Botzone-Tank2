# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 04:38:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 05:54:53

import os
import json
from pprint import pprint
from utils import to_stream, json_load

import sys
sys.path.append("../")

from core.botzone import Tank2Botzone
from core.map_ import Tank2Map
from core.const import MAP_WIDTH, MAP_HEIGHT


# DATA_DIR = "../dataset/5cc087a335f461309c283cc9/"
DATA_DIR = "../dataset/5cc004c335f461309c27e355/"

BLUE_INPUT_JSON = os.path.join(DATA_DIR, "blue.input.json")
RED_INPUT_JSON  = os.path.join(DATA_DIR, "red.input.json")

blueInputJSON = json_load(BLUE_INPUT_JSON)
redInputJSON  = json_load(RED_INPUT_JSON)


if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_)

    stream = to_stream(json.dumps(redInputJSON))

    terminal.handle_input(stream)