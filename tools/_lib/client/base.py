# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-28 01:46:07
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 03:24:27

__all__ = [

    "BaseClient",

    ]

import requests
from ..utils import json_load, json_dump


class BaseClient(object):

    TIMEOUT = 10
    HEADERS = {}

    def __init__(self, **kwargs):
        self._session = requests.session()
        self._session.headers.update(self.__class__.HEADERS)

    def _request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.__class__.TIMEOUT)
        return self._session.request(method, url, **kwargs)

    def _get(self, url, params=None, **kwargs):
        return self._request('GET', url,  params=params, **kwargs)

    def _post(self, url, data=None, json=None, **kwargs):
        return self._request('POST', url, data=data, json=json, **kwargs)
