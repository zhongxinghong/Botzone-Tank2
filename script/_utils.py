# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 06:10:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 16:56:15

__all__ = [

    "mkdir",
    "abs_path",
    "read_file",
    "json_load",

    ]


import os
import json

_ROOT_DIR = os.path.dirname(__file__)

def mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

def abs_path(*path):
    return os.path.abspath(os.path.join(_ROOT_DIR, *path))

def read_file(file, encoding="utf-8"):
    with open(file, "r", encoding=encoding) as fp:
        return fp.read()

def json_load(file):
    with open(file, "rb") as fp:
        return json.load(fp)