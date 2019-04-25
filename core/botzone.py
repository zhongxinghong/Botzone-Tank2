# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:33:03
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 10:07:02

__all__ = [

    "Tank2Botzone",

    ]

#{ BEGIN }#

import json
import sys


class Botzone(object):

    def __init__(self, long_running):
        self._longRunning = long_running
        self._data = None
        self._globalData = None
        self._requests = []  # 对方的决策
        self._responses = [] # 己方的决策


    def handle_input(self, stream):
        """
        解析输入信息

        Input:
            - stream   TextIOWrapper   输入流对象，必须实现 read 方法
        """
        inputJSON = json.loads(stream.read())

        self._requests   = inputJSON["requests"]
        self._responses  = inputJSON["responses"]
        self._data       = inputJSON.get("data", None)
        self._globalData = inputJSON.get("globaldata", None)

    def make_output(self, stream, response, debug, data, globaldata):
        """
        输出结果

        Input：
            - stream       TextIOWrapper   输出流对象，必须实现 write 方法
            - response     dict            Bot 此回合的输出信息
            - debug        str             调试信息，将被写入log，最大长度为1KB
            - data         dict            Bot 此回合的保存信息，将在下回合输入
            - globaldata   dict            Bot 的全局保存信息，将会在下回合输入，
                                             对局结束后也会保留，下次对局可以继续利用
        """
        stream.write(json.dumps({
            "response": response,
            "debug": debug,
            "data": data,
            "globaldata": globaldata,
            }))

        if not self._longRunning:
            sys.exit(0)



class Tank2Botzone(Botzone):

    def __init__(self, map, long_running=False):
        super().__init__(long_running)
        self._mySide = -1
        self._map = map


    @property
    def mySide(self):
        return self._mySide


    def _parse_field_points(self, binary):
        """
        解析 requests 中存在有某种类型 field 的坐标

        Input:
            - binary   list   某种类型 field 的 binary 标记
        Yield:
            - (x, y)   tuple(int, int)   这个坐标上存在该类型 field
        """
        _MAP_WIDTH = self._map.width
        for i in range(3):
            mask = 1
            for y in range(i * 3, i * 3 + 3):
                for x in range(_MAP_WIDTH):
                    if binary[i] & mask:
                        yield (x, y)
                    mask <<= 1

    def handle_input(self, stream=sys.stdin):

        super().handle_input(stream)

        header = self._requests.pop(0) # 此时 header 被去掉

        self._mySide = header["mySide"]

        for x, y in self._parse_field_points(header["brickfield"]):
            self._map.create_brick_field(x, y)

        for x, y in self._parse_field_points(header["steelfield"]):
            self._map.create_steel_field(x, y)

        for x, y in self._parse_field_points(header["waterfield"]):
            self._map.create_water_field(x, y)

        self._map.do_actions(self._mySide, self._responses, self._requests)


    def make_output(self, actions, stream=sys.stdout, **kwargs):
        debug = kwargs.get("debug", None)
        data = kwargs.get("data", None)
        globalData = kwargs.get("globaldata", None)
        super().make_output(stream, actions, debug, data, globalData)

#{ END }#