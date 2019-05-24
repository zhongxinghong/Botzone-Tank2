# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-23 18:19:15
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 18:23:05

__all__ = [

    "task_download_favorite_matches",

    ]

import os
from ...client.botzone import BotzoneClient
from ...client.bean import FavoriteMatchBean
from ...utils import json_load, json_dump
from ...log import ConsoleLogger
from ..const import CONFIG_JSON_FILE, FAVORITE_MATCHES_DATA_DIR
from ..utils import log_schedule_task


_logger = ConsoleLogger("scheduler.favorite_match")
_client = BotzoneClient()


@log_schedule_task(_logger, "fetch rank matches")
def task_download_favorite_matches():

    r = _client.get_favorites()
    respJson = r.json()

    matches = [ FavoriteMatchBean(match) for match in respJson["favorited_matches"] ]
    counter = 0
    for match in matches:
        file = os.path.join(FAVORITE_MATCHES_DATA_DIR, "%s.json" % match.id)
        if os.path.exists(file):
            continue
        json_dump(match.dict, file, ensure_ascii=False, indent=4)
        counter += 1

    _logger.info("downloaded %d new favorite matches" % counter)
