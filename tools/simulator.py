# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 11:25:35
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-26 01:25:58
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
game_const.DEBUG_MODE        = config["environment"]["debug"]         # 是否为 DEBUG 模式
game_const.LONG_RUNNING_MODE = config["environment"]["long_running"]  # 是否为 LONG_RUNNING 模式
game_const.SIMULATOR_ENV     = config["environment"]["simulator"]     # 是否为模拟器环境
game_const.COMPACT_MAP       = config["debug"]["compact_map"]         # 是否以紧凑的形式打印地图
game_const.SIMULATOR_PRINT   = config["simulator"]["print"]           # 是否输出模拟器日志

## 游戏相关 ##
MATCH_ID     = config["game"]["match_id"]      # 比赛 ID
SIDE         = config["game"]["side"]          # 我方属于哪一方，这决定了使用什么数据源。
                                               #     0 表示 blue.input.json, 1 表示 red.input.json
INITIAL_TURN = config["game"]["initial_turn"]  # 从哪一回合开始

## 模拟器配置 ##
TURN_INTERVAL  = config["simulator"]["turn_interval"]  #　在自动播放的情况下，每回合结束后时间间隔
PAUSE_PER_TURN = config["simulator"]["pause"]          # 设置为非自动播放，每回合结束后需要用户按下任意键继续
HIDE_DATA      = config["simulator"]["hide_data"]      # 是否隐藏游戏输出 json 中的 data 和 globaldata 字段


def main():

    from main import main as run_game

    if SIDE == 0:
        INPUT_JSON = os.path.join(DATASET_DIR, MATCH_ID, BLUE_INPUT_JSON_FILENAME)
    elif SIDE == 1:
        INPUT_JSON = os.path.join(DATASET_DIR, MATCH_ID, RED_INPUT_JSON_FILENAME)
    else:
        raise Exception("unknown side %s" % SIDE)

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

        outputJSON = json.loads(output)
        data = outputJSON.get("data")
        globaldata = outputJSON.get("globaldata")

        print(CUT_OFF_RULE)
        print("End Turn %s" % turn)

        if PAUSE_PER_TURN:
            #subprocess.call("pause",shell=True)
            os.system('pause')
        else:
            time.sleep(TURN_INTERVAL)


if __name__ == '__main__':

    main()