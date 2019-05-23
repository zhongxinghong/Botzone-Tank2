# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-23 15:07:11
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 16:08:09


__all__ = [

    "task_download_contest_matches",

    ]

import os
from lxml import etree
from ...client.botzone import BotzoneClient
from ...client.bean.contest import GroupContestBean
from ...utils import json_load, json_dump
from ...log import ConsoleLogger
from ..const import CONFIG_JSON_FILE, CONTEST_MATCHES_DATA_DIR
from ..utils import log_schedule_task


_logger = ConsoleLogger("scheduler.contest_match")
_client = BotzoneClient()


@log_schedule_task(_logger, "fetch contest matches")
def task_download_contest_matches():

    config = json_load(CONFIG_JSON_FILE)
    contestID = config["contest_match"]["contest_id"]
    groupID   = config["contest_match"]["group_id"]
    botID     = config["contest_match"]["bot_id"]
    gameName  = config["contest_match"]["game"]

    r = _client.get_contest_detail(contestID, groupID)
    contest = GroupContestBean(r.json(), gameName)

    counter = 0
    for match in contest.matches:
        file = os.path.join(CONTEST_MATCHES_DATA_DIR, "%s.json" % match.id)
        if os.path.exists(file):
            continue
        for bot in match.players:
            if bot.id == botID:
                json_dump(match.dict, file, ensure_ascii=False, indent=4)
                counter += 1

    _logger.info("Group: %s" % contest.group)
    _logger.info("Contest: %s" % contest.name)
    _logger.info("Game: %s" % contest.game)
    _logger.info("BotID: %s" % botID)
    _logger.info("downloaded %d new contest matches about this bot" % counter)
