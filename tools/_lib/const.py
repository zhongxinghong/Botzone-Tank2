# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 02:13:56
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 02:18:22

__all__ = [

    "ROOT_DIR",
    "CACHE_DIR",
    "CONFIG_DIR",

    ]


import os as _os


_BASE_DIR = _os.path.dirname(__file__)
_absP = lambda *path: _os.path.abspath(_os.path.join(_BASE_DIR, *path))


ROOT_DIR   = _absP("../")
CACHE_DIR  = _absP("../cache/")
CONFIG_DIR = _absP("../config/")