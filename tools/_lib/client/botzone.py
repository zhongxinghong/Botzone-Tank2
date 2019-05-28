# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 02:23:29
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-26 23:57:30

__all__ = [

    "BotzoneClient",

    ]

import os
import time
from .const import USER_AGENT
from .const import BOTZONE_URL_HOST, BOTZONE_URL_LOGIN, BOTZONE_URL_MYBOTS, BOTZONE_URL_BOT_DETAIL,\
        BOTZONE_URL_GLOBAL_MATCH_LIST, BOTZONE_URL_CONTEST_DETAIL, BOTZONE_URL_GROUP,\
        BOTZONE_URL_FAVORITES, BOTZONE_URL_REMOVE_FAVORITE_MATCH
from .base import BaseClient
from .cookies import CookiesManagerMixin
from .hooks import get_hooks, hook_check_status_code, hook_botzone_check_success_field
from ..utils import Singleton
from ..log import ConsoleLogger


_logger = ConsoleLogger("client.botzone")


class BotzoneClient(BaseClient, CookiesManagerMixin, metaclass=Singleton):

    USE_HTTP20 = False
    HOST = BOTZONE_URL_HOST
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Origin": BOTZONE_URL_HOST,
        "x-requested-with": "XMLHttpRequest",
        }

    def __init__(self):
        _logger.info("Botzone client launched")
        BaseClient.__init__(self)
        CookiesManagerMixin.__init__(self)
        _logger.info("load cookies")
        self._load_cookies() # 创建时自动导入本地 cookies 缓存


    def login(self, email, password):
        """
        登录 API

        """
        _logger.info("Email: %s" % email)
        _logger.info("login ...")

        r = self._post(
                url=BOTZONE_URL_LOGIN,
                data={
                    "email": email,
                    "password": password,
                },
                headers={
                    "Referer": BOTZONE_URL_HOST,
                },
                hooks=get_hooks(hook_check_status_code,
                                hook_botzone_check_success_field),
            )

        _logger.info("login successfully")

        self._save_cookies() # 保存 cookies

        _logger.info("save login cookies")
        #self._save_content(r, "login.html")
        return r


    def get_favorites(self):
        """
        获取玩家收藏
        """
        _logger.info("get favorites")

        r = self._get(
                url=BOTZONE_URL_FAVORITES,
                headers={
                    "Referer": BOTZONE_URL_HOST,
                },
                hooks=get_hooks(hook_check_status_code),
            )

        _logger.info("get favorites successfully")
        #self._save_content(r, "favorites.json")
        return r

    def remove_fovorite_match(self, matchID):
        """
        删除收藏的比赛
        """
        _logger.info("remove favorite match %s" % matchID)

        r = self._post(
                url=BOTZONE_URL_REMOVE_FAVORITE_MATCH,
                data={
                    "matchid": matchID,
                },
                headers={
                    "Referer": BOTZONE_URL_HOST,
                },
                hooks=get_hooks(hook_check_status_code,
                                hook_botzone_check_success_field),
            )

        _logger.info("remove favorite match %s successfully" % matchID)
        return r

    def get_mybots(self):
        """
        获取 My Bots 页

        """
        _logger.info("get mybots ...")

        r = self._get(
                url=BOTZONE_URL_MYBOTS,
                hooks=get_hooks(hook_check_status_code),
            )

        _logger.info("get mybots successfully")
        #self._save_content(r, "mybots.html")
        return r


    def get_bot_detail(self, botID):
        """
        获取 Bot 全部具体信息的

        """
        _logger.info("BotID: %s" % botID)
        _logger.info("get bot detail ...")

        r = self._get(
                url=BOTZONE_URL_BOT_DETAIL.format(botID=botID),
                params={
                    "_": int( time.time() * 1000 ),
                },
                headers={
                    "Referer": BOTZONE_URL_MYBOTS,
                },
                hooks=get_hooks(hook_check_status_code),
            )

        _logger.info("get bot detail successfully")
        #self._save_content(r, "bot_detail_%s.json" % botID)
        return r


    def get_global_match_list(self, gameID, startID="", endID=""):
        """
        获取全局的比赛记录

        """
        _logger.info("GameID: %s" % gameID)
        if startID != "":
            _logger.info("StartID: %s" % startID)
        _logger.info("get global match list ...")

        r = self._get(
                url=BOTZONE_URL_GLOBAL_MATCH_LIST,
                params={
                    "startid": startID,
                    "endid": endID,
                    "game": gameID,
                },
                hooks=get_hooks(hook_check_status_code),
            )

        _logger.info("get global match list successfully")
        #self._save_content(r, "global_match_list.html")
        return r


    def get_contest_detail(self, contestID, groupID):
        """
        获取小组赛的描述、玩家列表、比赛记录等
        """
        _logger.info("ContestID: %s" % contestID)
        _logger.info("get contest detail ...")

        r = self._get(
                url=BOTZONE_URL_CONTEST_DETAIL.format(contestID=contestID),
                headers={
                    "Referer": BOTZONE_URL_GROUP.format(groupID=groupID)
                },
                hooks=get_hooks(hook_check_status_code),
            )

        _logger.info("get contest detail successfully")
        #self._save_content(r, "contest_detail.json")
        return r
