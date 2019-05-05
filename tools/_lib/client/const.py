# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 14:43:52
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 17:09:45

__all__ = [

    "USER_AGENT",
    "BOTZONE_USER_JSON_FILE",

    "BOTZONE_URL_HOST",
    "BOTZONE_URL_LOGIN",
    "BOTZONE_URL_MYBOTS",
    "BOTZONE_URL_BOT_DETAIL"
    "BOTZONE_URL_MATCH",

    ]

from ..const import CACHE_DIR
from ..utils import abs_path


USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"

BOTZONE_USER_JSON_FILE = abs_path("./config/botzone_user.json")

BOTZONE_URL_HOST       = "https://botzone.org.cn"
BOTZONE_URL_LOGIN      = "https://botzone.org.cn/login"
BOTZONE_URL_MYBOTS     = "https://botzone.org.cn/mybots"
BOTZONE_URL_BOT_DETAIL = "https://botzone.org.cn/mybots/detail/{botID}"
BOTZONE_URL_MATCH      = "https://botzone.org.cn/match/{matchID}"