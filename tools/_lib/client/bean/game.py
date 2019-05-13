# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 16:21:04
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 04:14:30

__all__ = [

    "RankGameBean",

    ]

from .bot import RankBotBean
from ...utils import CachedProperty


class RankGameBean(object):

    def __init__(self, tree):
        self._tree = tree  # lxml.etree._Element  from etree.HTML(r.content)

    @CachedProperty
    def name(self):
        return self._tree.xpath('.//*[contains(@class, "panel-title")]')[0].text.strip()

    @CachedProperty
    def id(self):
        return self._tree.xpath('./ul/@id')[0].lstrip("game")

    @CachedProperty
    def bots(self):
        return [ RankBotBean(botTree, self) for botTree in self._tree.xpath('./ul/li') ]

    def __repr__(self):
        return "Game<%s, %s>" % (
                self.name, self.id)
