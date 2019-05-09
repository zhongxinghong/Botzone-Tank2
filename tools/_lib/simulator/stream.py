# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 11:41:00
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-09 12:38:49

__all__ = [

    "SimulatorConsoleInputStream",
    "SimulatorJSONFileInputStream",
    "SimulatorTextInputStream",

    "SimulatorConsoleOutputStream",

    ]

import json
from io import BytesIO
from pprint import pprint
from functools import wraps
from copy import deepcopy
from ..utils import json_load, b


class AbstractBotzoneIstream(object):

    def read(self, *args, **kwargs):
        raise NotImplementedError


class AbstractBotzoneOstream(object):

    def write(self, data, **kwargs):
        raise NotImplementedError


class SimulatorConsoleInputStream(AbstractBotzoneIstream):

    def read(self):
        return input()


class SimulatorJSONFileInputStream(AbstractBotzoneIstream):

    def __init__(self, file):
        self._file = file

    def read(self):
        obj = json_load(self._file)
        return json.dumps(obj)


class SimulatorTextInputStream(AbstractBotzoneIstream):

    def __init__(self, data):
        self._stream = BytesIO(b(data))

    def read(self):
        return self._stream.read()


class SimulatorConsoleOutputStream(AbstractBotzoneOstream):

    def __init__(self, connection, pretty=False, hide_data=False):
        self._connection = connection # 多进程交流
        self._pretty = pretty
        self._hide_data = hide_data

    def write(self, data):

        self._connection.send(data) # 发回去原始的 data

        if not self._hide_data:
            _data = data
        else:
            _raw = json.loads(data)
            _data = { k:v for k,v in _raw.items() if k != "data" }
            if "data" in _raw:
                _data["data"] = "hidden"
            if "globaldata" in _raw:
                _data["data"] = "hidden"

        if not self._pretty:
            print(_data)
        else:
            pprint(_data)
