# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 16:21:07
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 04:14:19

__all__ = [

    "RankBotBean"

    ]

import re
from ...utils import CachedProperty

_regexScore = re.compile(r'\d+(?:\.\d+)?')


class RankBotBean(object):

    def __init__(self, tree, game):
        self._tree = tree  # lxml.etree._Element  from RankGameBean
        self._game = game  # RankGameBean

    @property
    def game(self):
        return self._game

    @CachedProperty
    def id(self):
        return self._tree.xpath('./a/@data-botid')[0]

    @CachedProperty
    def name(self):
        return self._tree.xpath('.//*[@class="list-group-item-heading"]')[0].text

    @CachedProperty
    def version(self):
        _version = self._tree.xpath('.//*[contains(@class, "botversion")]/span')[0].text
        return int(_version)

    @CachedProperty
    def description(self):
        return self._tree.xpath('.//*[contains(@class, "botdesc")]')[0].text

    @CachedProperty
    def score(self):
        _botScoreText = self._tree.xpath('.//*[contains(@class, "rankscore")]')[0].text
        _botScore = _regexScore.search(_botScoreText).group()
        return float(_botScore)

    def __repr__(self):
        return "Bot<%s, %d, %.2f, %s>" % (
                self.name, self.version, self.score, self.id)