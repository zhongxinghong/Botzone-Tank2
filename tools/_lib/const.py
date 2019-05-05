# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 02:13:56
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 18:42:36

__all__ = [

    "CACHE_DIR",
    "CONFIG_DIR",
    "LOG_DIR",

    ]


import os as _os

# 为了让 const.py 不依赖于 utils.py
# 此处重新定义相关函数
#---------------------------------------
__BASE_DIR = _os.path.join(_os.path.dirname(__file__), "../")

def _absP(*path):
    return _os.path.abspath(_os.path.join(__BASE_DIR, *path))

def _mkdir(path):
    if not _os.path.exists(path):
        _os.mkdir(path)


CACHE_DIR  = _absP("./cache/")
CONFIG_DIR = _absP("./config/")
LOG_DIR    = _absP("./log/")


_mkdir(CACHE_DIR)
_mkdir(LOG_DIR)