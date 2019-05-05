# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 16:21:04
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 17:33:07

__all__ = [

    "GameBean",

    ]

from .bot import BotBean
from ...utils import CachedProperty


class GameBean(object):

    def __init__(self, tree):
        self._tree = tree  # lxml.etree._Element  from etree.HTML(r.content)

    @CachedProperty
    def name(self):
        return self._tree.xpath('.//*[contains(@class, "panel-title")]/text()')[0].strip()

    @CachedProperty
    def id(self):
        return self._tree.xpath('./ul/@id')[0].lstrip("game")

    @CachedProperty
    def bots(self):
        return [ BotBean(botTree, self) for botTree in self._tree.xpath('./ul/li') ]

    def __repr__(self):
        return "Game<%s, %s>" % (
                self.name, self.id)