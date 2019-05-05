# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 15:06:57
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-05 15:12:27

__all__ = [

    "ConsoleLogger",
    "FileLogger",

    ]

import os
import datetime
import logging
from .const import LOG_DIR


class BaseLogger(object):

    LEVEL  = logging.DEBUG
    FORMAT = logging.Formatter("[%(levelname)s] %(name)s, %(asctime)s, %(message)s", "%Y-%m-%d %H:%M:%S")
    #FORMAT = logging.Formatter("[%(levelname)s] %(name)s, %(asctime)s, %(message)s", "%H:%M:%S")

    def __init__(self, name):
        if self.__class__ is __class__:
            raise NotImplementedError
        self._name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(self.__class__.LEVEL)
        self._logger.addHandler(self._get_headler())

    @property
    def name(self):
        return self._name

    def _get_headler(self):
        raise NotImplementedError


    def log(self, level, msg, *args, **kwargs):
        return self._logger.log(level, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        return self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        return self._logger.info(msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        return self._logger.warn(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return self._logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        kwargs.setdefault("exc_info", True)
        return self._logger.exception(msg, *args, **kwargs)

    def fatal(self, msg, *args, **kwargs):
        return self._logger.fatal(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return self._logger.critical(msg, *args, **kwargs)



class ConsoleLogger(BaseLogger):
    """ 控制台日志输出类 """

    LEVEL = logging.DEBUG

    def _get_headler(self):
        """ 返回封装好的 console_headler """
        headler = logging.StreamHandler()
        headler.setLevel(self.__class__.LEVEL)
        headler.setFormatter(self.__class__.FORMAT)
        return headler


class FileLogger(BaseLogger):
    """ 文件日志输出类 """

    LEVEL = logging.WARNING

    def _get_headler(self):
        """ 返回封装好的  """
        filename = "%s.%s.log" % (
            self.name,
            datetime.date.strftime(datetime.date.today(), "%Y%m%d")
            )
        path = os.path.join(LOG_DIR, filename)
        headler = logging.FileHandler(path, encoding="utf-8")
        headler.setLevel(self.__class__.LEVEL)
        headler.setFormatter(self.__class__.FORMAT)
        return headler