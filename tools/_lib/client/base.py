# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 01:46:07
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 21:28:00

__all__ = [

    "BaseClient",

    ]

import os
import requests
from hyper.contrib import HTTP20Adapter
from ..utils import json_load, json_dump
from ..const import CACHE_DIR


class BaseClient(object):

    USE_HTTP20 = False
    HOST       = ""
    TIMEOUT    = 10
    HEADERS    = {}

    def __init__(self, **kwargs):
        self._session = requests.session()
        _cls = self.__class__
        if _cls.USE_HTTP20:
            assert _cls.HOST is not None, "HOST must be set for client %s" % _cls.__name__
            self._session.mount(_cls.HOST, HTTP20Adapter())
        self._session.headers.update(_cls.HEADERS)

    def _request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.__class__.TIMEOUT)
        return self._session.request(method, url, **kwargs)

    def _get(self, url, params=None, **kwargs):
        return self._request('GET', url,  params=params, **kwargs)

    def _post(self, url, data=None, json=None, **kwargs):
        return self._request('POST', url, data=data, json=json, **kwargs)

    @staticmethod
    def _save_content(r, filename):
        file = os.path.join(CACHE_DIR, filename)
        with open(file, "wb") as fp:
            fp.write(r.content)

