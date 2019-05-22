# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-01 01:58:22
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-21 15:30:38

__all__ = [

    "BLANK_LINES",
    "CONFIG_JSON_FILE",
    "BUILD_DIR",

    ]

from ..utils import get_abspath

BLANK_LINES = "\n\n"
CONFIG_JSON_FILE = get_abspath("./config/builder.json")
BUILD_DIR        = get_abspath("../build")