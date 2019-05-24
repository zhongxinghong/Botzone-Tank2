# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 01:58:58
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 19:14:50

__all__ = [

    "CookiesManagerMixin",

    ]

import os
from requests.cookies import RequestsCookieJar
from ..utils import json, json_load, json_dump
from ..const import CACHE_DIR


class CookiesManagerMixin(object):
    """
    cookies 管理相关的 mixin

    需要被一个优先继承了 BaseClient 的类多重继承

    """
    def __init__(self):
        if not hasattr(self, "_session"):
            raise Exception("self must be inited by BaseClient.__init__ first")

    @property
    def _cookies_file(self):
        filename = "%s.cookies.json" % self.__class__.__name__
        return os.path.abspath(os.path.join(CACHE_DIR, filename))

    def _save_cookies(self):
        json_dump(self._session.cookies.get_dict(), self._cookies_file)

    def _load_cookies(self):
        try:
            cookies = json_load(self._cookies_file)
        except (FileNotFoundError, json.JSONDecodeError):
            jar = RequestsCookieJar()
        else:
            jar = RequestsCookieJar()
            for k, v in cookies.items():
                jar.set(k, v)
        finally:
            self._session.cookies = jar

    def clear_cookies(self):
        self._session.cookies.clear()

    def refresh_cookies(self):
        self._load_cookies()