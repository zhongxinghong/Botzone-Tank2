# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-21 15:46:28
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-21 22:53:45

__all__ = [

    "AppConfig",

    ]

import time
from ..client.utils import format_timestamp


class AppConfig(object):

    DEBUG = True
    TESTING = False
    JSON_SORT_KEYS = False
    JSON_AS_ASCII = False

    @staticmethod
    def init_app(app):
        app.jinja_env.filters["strftime"] = format_timestamp
        app.jinja_env.globals["get_timestamp"] = lambda: int( time.time()* 1000 )
