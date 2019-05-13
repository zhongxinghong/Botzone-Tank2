# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-14 03:34:06
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 03:59:28

__all__ = [

    "task_botzone_login",

    ]

from ...client.botzone import BotzoneClient
from ...client.const import BOTZONE_USER_JSON_FILE
from ...utils import json_load
from ...log import ConsoleLogger
from ..utils import log_schedule_task


_logger = ConsoleLogger("scheduler.login")
_client = BotzoneClient()


@log_schedule_task(_logger, "login botzone")
def task_botzone_login():

    userInfo = json_load(BOTZONE_USER_JSON_FILE)
    if userInfo is None:
        raise Exception("can't load user config from %r" % BOTZONE_USER_JSON_FILE)

    email    = userInfo.get("email")
    password = userInfo.get("password")

    if email is None:
        raise Exception("field 'email' is missing")
    if password is None:
        raise Exception("field 'password' is missing")

    r = _client.login(email, password)
