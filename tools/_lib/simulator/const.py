# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 11:54:55
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-21 15:30:45

__all__ = [

    "BLUE_INPUT_JSON_FILENAME",
    "RED_INPUT_JSON_FILENAME",

    "DATASET_DIR"
    "CONFIG_JSON_FILE",

    ]

import os
from ..utils import get_abspath

BLUE_INPUT_JSON_FILENAME = "blue.input.json"
RED_INPUT_JSON_FILENAME  = "red.input.json"
DATASET_DIR              = get_abspath("../dataset/")
CONFIG_JSON_FILE         = get_abspath("./config/simulator.json")