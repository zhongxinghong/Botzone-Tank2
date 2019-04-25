# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 08:42:04
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 10:07:18

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