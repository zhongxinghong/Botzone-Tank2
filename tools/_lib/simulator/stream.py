# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 11:41:00
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 13:57:18

__all__ = [

    "SimulatorConsoleInputStream",
    "SimulatorJSONFileInputStream",
    "SimulatorTextInputStream",

    "SimulatorConsoleOutputStream",

    ]

import json
from io import BytesIO
from pprint import pprint
from ..utils import json_load, b


class AbstractBotzoneIstream(object):

    def read(self, *args, **kwargs):
        raise NotImplementedError


class AbstractBotzoneOstream(object):

    def writer(self, data, **kwargs):
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

    def __init__(self, pretty=False):
        self._pretty = pretty

    def write(self, data):
        if not self._pretty:
            print(data)
        else:
            pprint(data)
