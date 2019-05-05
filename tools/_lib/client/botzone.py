# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 02:23:29
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 18:33:42

__all__ = [

    "BotzoneClient",

    ]

import os
import time
from .const import USER_AGENT
from .const import BOTZONE_URL_HOST, BOTZONE_URL_LOGIN, BOTZONE_URL_MYBOTS, BOTZONE_URL_BOT_DETAIL
from .base import BaseClient
from .cookies import CookiesManagerMixin
from .hooks import get_hooks, hook_check_status_code, hook_botzone_check_success_field
from ..utils import Singleton
from ..log import ConsoleLogger


_logger = ConsoleLogger("client.botzone")


class BotzoneClient(BaseClient, CookiesManagerMixin, metaclass=Singleton):

    HEADERS = {
        "User-Agent": USER_AGENT,
        "Origin": BOTZONE_URL_HOST,
        "x-requested-with": "XMLHttpRequest",
        }

    def __init__(self):
        BaseClient.__init__(self)
        CookiesManagerMixin.__init__(self)
        self._session.cookies = self._load_cookies() # 创建时自动导入本地 cookies
        _logger.info("load cookies")


    def login(self, email, password):
        """
        登录 API

        """
        _logger.info("Email: %s" % email)
        _logger.info("login ...")

        r = self._post(BOTZONE_URL_LOGIN,
                data={
                    "email": email,
                    "password": password,
                }, headers={
                    "Referer": BOTZONE_URL_HOST,
                }, hooks=get_hooks(hook_check_status_code,
                                   hook_botzone_check_success_field),
            )

        _logger.info("login successfully")

        self._save_cookies() # 保存 cookies

        _logger.info("save login cookies")
        #self._save_content(r, "login.html")
        return r


    def get_mybots(self):
        """
        获取 My Bots 页

        """
        _logger.info("get mybots ...")

        r = self._get(BOTZONE_URL_MYBOTS)

        _logger.info("get mybots successfully")
        #self._save_content(r, "mybots.html")
        return r


    def get_bot_detail(self, botID):
        """
        获取 Bot 全部具体信息的 API

        """
        _logger.info("BotID: %s" % botID)
        _logger.info("get bot detail ...")

        r = self._get(BOTZONE_URL_BOT_DETAIL.format(botID=botID),
                params={
                    "_": int( time.time() * 1000 ),
                }, headers={
                    "Referer": BOTZONE_URL_MYBOTS,
                })

        _logger.info("get bot detail successfully")
        #self._save_content(r, "bot_detail_%s.json" % botID)
        return r