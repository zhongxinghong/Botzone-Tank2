# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 16:21:07
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 17:17:24

__all__ = [

    "BotBean"

    ]

import re
from ...utils import CachedProperty

_regexScore = re.compile(r'\d+(?:\.\d+)?')


class BotBean(object):

    def __init__(self, tree, game):
        self._tree = tree  # lxml.etree._Element  from GameBean
        self._game = game  # GameBean

    @property
    def game(self):
        return self._game

    @CachedProperty
    def id(self):
        return self._tree.xpath('./a/@data-botid')[0]

    @CachedProperty
    def name(self):
        return self._tree.xpath('.//*[@class="list-group-item-heading"]/text()')[0]

    @CachedProperty
    def version(self):
        _version = self._tree.xpath('.//*[contains(@class, "botversion")]/span/text()')[0]
        return int(_version)

    @CachedProperty
    def description(self):
        return self._tree.xpath('.//*[contains(@class, "botdesc")]/text()')[0]

    @CachedProperty
    def score(self):
        _botScoreText = self._tree.xpath('.//*[contains(@class, "rankscore")]/text()')[0]
        _botScore = _regexScore.search(_botScoreText).group()
        return float(_botScore)

    def __repr__(self):
        return "Bot<%s, %d, %.2f, %s>" % (
                self.name, self.version, self.score, self.id)