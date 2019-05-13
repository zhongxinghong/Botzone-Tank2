# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-14 03:38:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 04:05:06

__all__ = [

    "task_download_global_matches",

    ]

import os
from lxml import etree
from ...client.botzone import BotzoneClient
from ...client.bean import GlobalMatchBean
from ...utils import json_load, json_dump
from ...log import ConsoleLogger
from ..const import CONFIG_JSON_FILE, GLOBAL_MATCHES_DATA_DIR
from ..utils import log_schedule_task


_logger = ConsoleLogger("schedule.global_match")
_client = BotzoneClient()


@log_schedule_task(_logger, "fetch global matches")
def task_download_global_matches():

    config = json_load(CONFIG_JSON_FILE)
    gameID = config["global_match"]["game_id"]
    botID  = config["global_match"]["bot_id"]

    r = _client.get_global_match_list(gameID)
    tree = etree.HTML(r.content)
    matches = [ GlobalMatchBean(tr)
                    for tr in tree.xpath('//body/div[@class="container"]//table//tr[position()>1]') ]

    counter = 0
    for match in matches:
        file = os.path.join(GLOBAL_MATCHES_DATA_DIR, "%s.json" % match.id)
        if os.path.exists(file):
            continue
        for player in match.players:
            if player.isBot and player.botID == botID:
                json_dump(match.dict, file, ensure_ascii=False, indent=4)
                counter += 1
                break

    _logger.info("botID: %s" % botID)
    _logger.info("downloaded %d new global matches about this bot" % counter)
