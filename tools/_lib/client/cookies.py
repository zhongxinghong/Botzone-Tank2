# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 01:58:58
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 01:51:12

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
            cookies = RequestsCookieJar()
        else:
            if cookies is None:
                cookies = RequestsCookieJar()
            else:
                cookies = RequestsCookieJar()
                for k, v in cookies.items():
                    cookies.set(k, v)
        finally:
            self._session.cookies = cookies

    def clear_cookies(self):
        self._session.cookies.clear()
