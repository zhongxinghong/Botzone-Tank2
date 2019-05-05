# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 19:55:33
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-05 20:01:13

__all__ = [

    "parse_utc_timestamp",

    ]


import datetime


def parse_utc_timestamp(utc):
    """
    解析服务器发回来的 UTC 时间戳

    形如： 2017-07-28T08:28:47.776Z

    """
    UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    utcTime = datetime.datetime.strptime(utc, UTC_FORMAT)
    localTime = utcTime + datetime.timedelta(hours=8)
    return localTime