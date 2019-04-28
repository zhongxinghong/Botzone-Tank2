# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 02:23:29
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 02:50:39

__all__ = [


    ]

import os
from .base import BaseClient
from .cookies import CookiesManagerMixin
from .hooks import get_hooks, hook_check_status_code, hook_botzone_check_success_field
from ..utils import Singleton, json_load
from ..const import CONFIG_DIR


_USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"

_BOTZONE_USER_JSON_FILE = os.path.abspath(os.path.join(CONFIG_DIR, "botzone_user.json"))


class BotzoneClient(BaseClient, CookiesManagerMixin, metaclass=Singleton):

    HEADERS = {
        "User-Agent": _USER_AGENT,
        "Origin": "https://botzone.org.cn",
        }

    def __init__(self):
        BaseClient.__init__(self)
        CookiesManagerMixin.__init__(self)
        self._session.cookies = self._load_cookies() # 创建时自动导入本地 cookies

    def login(self):
        """
        登录接口
        """
        userInfo = json_load(_BOTZONE_USER_JSON_FILE)
        if userInfo is None:
            raise Exception("can't load user config from %r" % _BOTZONE_USER_JSON_FILE)

        email    = userInfo.get("email")
        password = userInfo.get("password")

        if email is None:
            raise Exception("field 'email' is missing")
        if password is None:
            raise Exception("field 'password' is missing")

        r = self._post(
                "https://botzone.org.cn/login",
                data={
                    "email": email,
                    "password": password,
                }, headers={
                    "Referer": "https://botzone.org.cn/",
                    "x-requested-with": "XMLHttpRequest",
                }, hooks=get_hooks(hook_check_status_code,
                                   hook_botzone_check_success_field),
            )

        self._save_cookies() # 保存 cookies