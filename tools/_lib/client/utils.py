# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 19:55:33
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 04:19:59

__all__ = [

    "parse_timestamp",
    "parse_utc_timestamp",

    ]


import datetime


def parse_timestamp(timestamp):
    """
    解析服务器发回来的时间戳

    形如： 2019-5-14 4:04:26

    Return:
        - time   datetime.datetime

    """
    return datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")


def parse_utc_timestamp(timestamp):
    """
    解析服务器发回来的 UTC 时间戳

    形如： 2017-07-28T08:28:47.776Z

    Return:
        - time   datetime.datetime

    """
    UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    utcTime = datetime.datetime.strptime(timestamp, UTC_FORMAT)
    localTime = utcTime + datetime.timedelta(hours=8)
    return localTime

