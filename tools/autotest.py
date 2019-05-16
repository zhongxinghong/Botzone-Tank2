# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-04 02:40:01
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-16 17:31:20
"""
自动化测试工具
------------------

让 bot 过一遍特定的数据集
如果出现 bug 就可以及时修复 ...

和 simulator 使用相同的壳

"""

import sys
sys.path.append("../")

from core import const as game_const

import os
import re
import time
import json
import subprocess
import multiprocessing
from _lib.utils import json_load
from _lib.simulator.const import BLUE_INPUT_JSON_FILENAME, RED_INPUT_JSON_FILENAME, DATASET_DIR
from _lib.simulator.utils import cut_by_turn
from _lib.simulator.stream import SimulatorConsoleOutputStream, SimulatorTextInputStream
from _lib.autotest.const import CONFIG_JSON_FILE

try:
    config = json_load(CONFIG_JSON_FILE)
except json.JSONDecodeError as e: # 配置文件写错
    raise e

## 环境变量设置 ##
game_const.DEBUG_MODE        = config["environment"]["debug"]
game_const.LONG_RUNNING_MODE = config["environment"]["long_running"]

DATASET = config["dataset"]

CUT_OFF_LINE = "-" * 60

def main():

    from main import main as run_game

    inputJSONFiles = []

    for matchID in DATASET:
        blueInputJSONFile = os.path.join(DATASET_DIR, matchID, BLUE_INPUT_JSON_FILENAME)
        redInputJSONFile = os.path.join(DATASET_DIR, matchID, RED_INPUT_JSON_FILENAME)
        if os.path.exists(blueInputJSONFile):
            inputJSONFiles.append(blueInputJSONFile)
        if os.path.exists(redInputJSONFile):
            inputJSONFiles.append(redInputJSONFile)

    inputJSONFiles = [ os.path.abspath(file) for file in inputJSONFiles ] # to abspath

    parentConnection, childrenConnection = multiprocessing.Pipe()

    for file in inputJSONFiles:
        try:
            wholeInputJSON = json_load(file)
        except json.JSONDecodeError as e:
            print("[Error] failed to load %s" % file)
            continue


        print("Case %s" % file)
        print(CUT_OFF_LINE)

        data = None
        globaldata = None

        totalTurn = len(wholeInputJSON["responses"])

        for turn in range(1, totalTurn+2):

            inputJSON = cut_by_turn(wholeInputJSON, turn)
            if data is not None:
                inputJSON["data"] = data
            if globaldata is not None:
                inputJSON["globaldata"] = globaldata

            istream = SimulatorTextInputStream(json.dumps(inputJSON))
            ostream = SimulatorConsoleOutputStream(connection=childrenConnection, hide_data=True)


            p = multiprocessing.Process( target=run_game, args=(istream, ostream) )
            p.daemon = True
            p.start()
            output = parentConnection.recv()
            p.join()

            if p.exitcode != 0:
                break

            outputJSON = json.loads(output)
            data = outputJSON.get("data")
            globaldata = outputJSON.get("globaldata")

        if data is not None:
            inputJSON["data"] = data

        print('')


if __name__ == '__main__':

    main()