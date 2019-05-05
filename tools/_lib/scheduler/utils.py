# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 18:07:45
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 18:24:03

__all__ = [

    "log_schedule_task",

    ]

from functools import wraps

_CUT_OFF_RULE = "-" * 30


def log_schedule_task(logger, name=None):
    """
    输出 schedule 的日志
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            nonlocal name
            name = name or func.__name__

            logger.info("task start: %s" % name)
            logger.info(_CUT_OFF_RULE)

            res = func(*args, **kwargs)

            logger.info(_CUT_OFF_RULE)
            logger.info("task end: %s" % name)

            return res
        return wrapper
    return decorator




