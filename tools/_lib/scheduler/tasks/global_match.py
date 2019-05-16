# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-14 03:38:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-16 17:23:40

__all__ = [

    "task_download_global_matches",
    "task_download_previous_global_matches",

    ]

import os
import time
from lxml import etree
from urllib.parse import urlparse, parse_qs
from ...client.botzone import BotzoneClient
from ...client.bean import GlobalMatchBean
from ...client.utils import format_timestamp
from ...utils import json_load, json_dump
from ...log import ConsoleLogger
from ..const import CONFIG_JSON_FILE, GLOBAL_MATCHES_DATA_DIR, REQUESTS_INTERVAL, REQUESTS_INTERVAL
from ..utils import log_schedule_task


_logger = ConsoleLogger("schedule.global_match")
_client = BotzoneClient()


@log_schedule_task(_logger, "fetch global matches")
def task_download_global_matches():
    """
    下载第一页内与特定 bot 相关的全局的比赛记录
    """
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


@log_schedule_task(_logger, "fetch previous global matches")
def task_download_previous_global_matches():
    """
    下载从本地记录所保存的最新的 matchID 至今的所有和特定 bot 相关的全局比赛记录
    如果本地缓存为空，则不执行这个任务
    """
    config = json_load(CONFIG_JSON_FILE)
    gameID = config["global_match"]["game_id"]
    botID  = config["global_match"]["bot_id"]

    matchIDs = [ filename.rstrip(".json") for filename
                    in os.listdir(GLOBAL_MATCHES_DATA_DIR) if filename.endswith(".json") ]

    if len(matchIDs) == 0:
        _logger.info("no local records, the latest matchID can't be determined")
        return

    else:
        latestMatchID = max(matchIDs)
        latestMatchTime = None

        while True:

            _logger.info("latest matchID: %s" % latestMatchID)
            if latestMatchTime is not None:
                _logger.info("latest match time: %s" % format_timestamp(latestMatchTime) )

            r = _client.get_global_match_list(gameID, endID=latestMatchID) # 从后往前找

            if len(r.history) > 0: # 发生了 302 重定向，原因是无更新记录，这就到达了任务终点
                querys = parse_qs( urlparse(r.url).query )
                msg = querys.get("msg")
                if msg is not None and msg[0] == "nomore":
                    _logger.info("no more matches")
                    break
                else:
                    _logger.warning("API has changed, msg == %s" % msg)
                    break

            tree = etree.HTML(r.content)
            matches = [ GlobalMatchBean(tr)
                            for tr in tree.xpath('//body/div[@class="container"]//table//tr[position()>1]') ]

            if len(matches) == 0: # 找到了终点
                break

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
            _logger.info("downloaded %d previous new global matches about this bot" % counter)

            latestMatchID = matches[0].id
            latestMatchTime = matches[0].time

            time.sleep(REQUESTS_INTERVAL)
            _logger.info("sleep %.2f s" % REQUESTS_INTERVAL)
