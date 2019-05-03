# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 11:25:35
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-04 03:09:51
"""
无 GUI 的游戏模拟器，可以模拟播放比赛记录

"""
import sys
sys.path.append("../")

from core import const as game_const

import os
import time
import json
import subprocess
import multiprocessing
from _lib.utils import json_load
from _lib.simulator.const import BLUE_INPUT_JSON_FILENAME, RED_INPUT_JSON_FILENAME,\
                                DATASET_DIR, CONFIG_JSON_FILE
from _lib.simulator.utils import cut_by_turn
from _lib.simulator.stream import SimulatorConsoleOutputStream, SimulatorTextInputStream

try:
    config = json_load(CONFIG_JSON_FILE)
except json.JSONDecodeError as e: # 配置文件写错
    raise e

## 环境变量设置 ##
game_const.DEBUG_MODE        = config["environment"]["debug"]
game_const.LONG_RUNNING_MODE = config["environment"]["long_running"]
game_const.SIMULATOR_ENV     = config["environment"]["simulator"]
game_const.COMPACT_MAP       = config["debug"]["compact_map"]
game_const.SIMULATOR_PRINT   = config["simulator"]["print"]

## 游戏相关 ##
MATCH_ID     = config["game"]["match_id"]
SIDE         = config["game"]["side"]
INITIAL_TURN = config["game"]["initial_turn"]

## 模拟器配置 ##
TURN_INTERVAL  = config["simulator"]["turn_interval"]
PAUSE_PER_TURN = config["simulator"]["pause"]
DATA_SOURCE    = config["simulator"]["data_source"]
HIDE_DATA      = config["simulator"]["hide_data"]


def main():

    from main import main as run_game

    if DATA_SOURCE == 0:
        INPUT_JSON = os.path.join(DATASET_DIR, MATCH_ID, BLUE_INPUT_JSON_FILENAME)
    elif DATA_SOURCE == 1:
        INPUT_JSON = os.path.join(DATASET_DIR, MATCH_ID, RED_INPUT_JSON_FILENAME)
    else:
        raise Exception("unknown side %s" % DATA_SOURCE)

    wholeInputJSON = json_load(INPUT_JSON)

    totalTurn = len(wholeInputJSON["responses"])

    data = None
    globaldata = None

    parentConnection, childrenConnection = multiprocessing.Pipe()

    for turn in range(INITIAL_TURN, totalTurn+2):

        CUT_OFF_RULE = "-" * 30

        inputJSON = cut_by_turn(wholeInputJSON, turn)
        if data is not None:
            inputJSON["data"] = data
        if globaldata is not None:
            inputJSON["globaldata"] = globaldata

        istream = SimulatorTextInputStream(json.dumps(inputJSON))
        ostream = SimulatorConsoleOutputStream(connection=childrenConnection, hide_data=HIDE_DATA)

        p = multiprocessing.Process( target=run_game, args=(istream, ostream) )
        p.daemon = True
        p.start()
        output = parentConnection.recv()
        p.join()

        if p.exitcode != 0:
            break

        data = json.loads(output).get("data")

        print(CUT_OFF_RULE)
        print("End Turn %s" % turn)

        if PAUSE_PER_TURN:
            subprocess.call("pause",shell=True)
        else:
            time.sleep(TURN_INTERVAL)


if __name__ == '__main__':

    main()