# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-14 03:35:25
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 03:59:39

__all__ = [

    "task_download_rank_matches",

    ]

import os
from ...client.botzone import BotzoneClient
from ...client.bean import RankMatchBean
from ...utils import json_load, json_dump
from ...log import ConsoleLogger
from ..const import CONFIG_JSON_FILE, RANK_MATCHES_DATA_DIR
from ..utils import log_schedule_task


_logger = ConsoleLogger("scheduler.rank_match")
_client = BotzoneClient()


@log_schedule_task(_logger, "fetch rank matches")
def task_download_rank_matches():

    config = json_load(CONFIG_JSON_FILE)
    botID  = config["rank_match"]["bot_id"]

    r = _client.get_bot_detail(botID)

    respJson = r.json()

    matches = [ RankMatchBean(match) for match in respJson["bot"]["rank_matches"] ]
    counter = 0
    for match in matches:
        file = os.path.join(RANK_MATCHES_DATA_DIR, "%s.json" % match.id)
        if os.path.exists(file):
            continue
        json_dump(match.dict, file, ensure_ascii=False, indent=4)
        counter += 1

    _logger.info("downloaded %d new rank matches" % counter)
