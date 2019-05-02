# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 08:42:04
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-02 22:40:20
"""
I/O 流

为不同的 I/O 方式提供统一的接口
"""

__all__ = [

    "BotzoneIstream",
    "BotzoneOstream",

    ]

#{ BEGIN }#

class BotzoneIstream(object):

    def read(self):
        return input()


class BotzoneOstream(object):

    def write(self, data):
        print(data)

#{ END }#