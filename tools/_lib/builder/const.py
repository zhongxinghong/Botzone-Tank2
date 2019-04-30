# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-01 01:58:22
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 02:22:14

__all__ = [

    "BLANK_LINES",
    "CONFIG_JSON_FILE",
    "BUILD_DIR",

    ]

from ..utils import abs_path

BLANK_LINES = "\n\n"
CONFIG_JSON_FILE = abs_path("./config/builder.json")
BUILD_DIR        = abs_path("../build")