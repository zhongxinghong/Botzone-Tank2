# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 17:46:05
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 18:18:47

__all__ = [

    "REQUESTS_INTERVAL",

    "CONFIG_JSON_FILE",

    "RANK_MATCHES_DATA_DIR",
    "GLOBAL_MATCHES_DATA_DIR",
    "CONTEST_MATCHES_DATA_DIR",
    "FAVORITE_MATCHES_DATA_DIR",

    ]

from ..utils import get_abspath, mkdir


REQUESTS_INTERVAL = 1  # 1s

CONFIG_JSON_FILE          = get_abspath("./config/scheduler.json")

RANK_MATCHES_DATA_DIR     = get_abspath("./data/rank_matches")
GLOBAL_MATCHES_DATA_DIR   = get_abspath("./data/global_matches")
CONTEST_MATCHES_DATA_DIR  = get_abspath("./data/contest_matches")
FAVORITE_MATCHES_DATA_DIR = get_abspath("./data/favorite_matches")


mkdir(RANK_MATCHES_DATA_DIR)
mkdir(GLOBAL_MATCHES_DATA_DIR)
mkdir(CONTEST_MATCHES_DATA_DIR)
mkdir(FAVORITE_MATCHES_DATA_DIR)