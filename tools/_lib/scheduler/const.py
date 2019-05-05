# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 17:46:05
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 18:42:24

__all__ = [

    "CONFIG_JSON_FILE",

    ]

from ..utils import abs_path, mkdir


CONFIG_JSON_FILE      = abs_path("./config/scheduler.json")
RANK_MATCHES_DATA_DIR = abs_path("./data/rank_matches")


mkdir(RANK_MATCHES_DATA_DIR)