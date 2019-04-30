# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 11:54:55
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 02:03:45

__all__ = [

    "BLUE_INPUT_JSON_FILENAME",
    "RED_INPUT_JSON_FILENAME",

    "DATASET_DIR"
    "CONFIG_JSON_FILE",

    ]

import os
from ..utils import abs_path

BLUE_INPUT_JSON_FILENAME = "blue.input.json"
RED_INPUT_JSON_FILENAME  = "red.input.json"
DATASET_DIR              = abs_path("../dataset/")
CONFIG_JSON_FILE         = abs_path("./config/simulator.json")