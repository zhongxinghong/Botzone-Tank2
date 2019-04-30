# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-01 02:06:28
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 02:07:23

__all__ = [

    "SourceBean",

    ]

import os
from ..utils import abs_path


class SourceBean(object):
    """
    src.json 中每个 src file 的 Bean 类

    struct:　{
        "pacakge": str,
        "file": str,
    }
    """
    def __init__(self, src):
        self._file     = abs_path(src["file"])
        self._package  = src["package"]
        self._disabled = src.get("disabled", False)

    @property
    def file(self):
        """
        src file 的绝对路径
        """
        return self._file

    @property
    def package(self):
        r"""
        package 名称，可以添加到 filename 前方

        WARNING:
            - 前后不能带任何 "/", "\" 路径分隔符
        """
        return self._package

    @property
    def filename(self):
        """
        src filename 文件名
        """
        return os.path.basename(self._file)

    @property
    def fullname(self):
        """
        添加了 package 前缀的 filename
        """
        _DELIMETER = "/"
        return _DELIMETER.join([self._package, self.filename]).strip(_DELIMETER)

    @property
    def disabled(self):
        return self._disabled