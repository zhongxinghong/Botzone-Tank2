# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 17:46:05
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-16 16:31:30

__all__ = [

    "REQUESTS_INTERVAL",

    "CONFIG_JSON_FILE",

    "RANK_MATCHES_DATA_DIR",
    "GLOBAL_MATCHES_DATA_DIR",

    ]

from ..utils import abs_path, mkdir


REQUESTS_INTERVAL       = 1 # 1s

CONFIG_JSON_FILE        = abs_path("./config/scheduler.json")

RANK_MATCHES_DATA_DIR   = abs_path("./data/rank_matches")
GLOBAL_MATCHES_DATA_DIR = abs_path("./data/global_matches")


mkdir(RANK_MATCHES_DATA_DIR)
mkdir(GLOBAL_MATCHES_DATA_DIR)