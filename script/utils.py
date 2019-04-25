# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 06:10:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 06:28:17

__all__ = [

    "mkdir",
    "read_file",

    ]


import os


def mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)

def read_file(file, encoding="utf-8"):
    with open(file, "r", encoding=encoding) as fp:
        return fp.read()