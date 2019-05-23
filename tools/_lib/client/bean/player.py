# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 17:02:55
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 15:59:03

__all__ = [

    "RankBotPlayerBean",
    "GroupContestParticipantBean",
    "GlobalMatchPlayerBean",
    "GroupContestBotPlayerBean",

    ]

import re
from ...utils import CachedProperty

_regexBotIDFromFavorite = re.compile(r'AddFavoriteBot\(this,\s*\'(\S+?)\',\s*(?:\d+)\)')


class RankBotPlayerBean(object):

    def __init__(self, json):
        self._json = json

    @CachedProperty
    def id(self):
        return self._json["_id"]

    @CachedProperty
    def type(self):
        return self._json["type"]

    @CachedProperty
    def userName(self):
        return self._json["bot"]["user"]["name"]

    @CachedProperty
    def botName(self):
        return self._json["bot"]["bot"]["name"]

    @CachedProperty
    def userID(self):
        return self._json["bot"]["user"]["_id"]

    @CachedProperty
    def botID(self):
        return self._json["bot"]["bot"]["_id"]

    def __repr__(self):
        return "BotPlayer(%s, %s)" % (
                self.botName, self.userName)

class GroupContestParticipantBean(RankBotPlayerBean):
    pass


'''
{
    "_id": "5cce9c5da51e681f0e8e2923",
    "type": "bot",
    "bot":
    {
        "_id": "5cce9391a51e681f0e8e22d6",
        "ver": 8,
        "bot":
        {
            "score": 1210.7367088328535,
            "opensource": false,
            "ranked": true,
            "_id": "5ccd7355a51e681f0e8d2c55",
            "name": "Akyuu_no_Q"
        },
        "user":
        {
            "_id": "5c40639734299b1d1ec90a59",
            "name": "tlzmybm"
        }
    }
}
'''

class GlobalMatchPlayerBean(object):

    def __init__(self, tree):
        self._tree = tree

    @CachedProperty
    def userID(self):
        _href = self._tree.xpath('./a[@class="username" or @class="smallusername"]/@href')[0]
        return _href.split("/")[-1]

    @CachedProperty
    def userName(self):
        return self._tree.xpath('./a[@class="username" or @class="smallusername"]')[0].text

    @CachedProperty
    def score(self):
        _score = self._tree.find('./div[1]').text
        return int(_score)

    @CachedProperty
    def isBot(self):
        return "botblock" in self._tree.attrib["class"]

    @CachedProperty
    def botName(self):
        self._raise_if_not_a_bot()
        return self._tree.xpath('./a[contains(@class, "botname")]')[0].text.strip()

    @CachedProperty
    def botID(self):
        self._raise_if_not_a_bot()
        _onclick = self._tree.xpath('./a[contains(@class, "favorite")]/@onclick')[0]
        return _regexBotIDFromFavorite.match(_onclick).group(1)

    @CachedProperty
    def botVersion(self):
        self._raise_if_not_a_bot()
        _version = self._tree.xpath('./a[contains(@class, "botname")]/span[@class="version"]')[0].text
        return int(_version)

    def _raise_if_not_a_bot(self):
        if not self.isBot:
            raise Exception("I'm not a bot player")

    def __repr__(self):
        if not self.isBot:
            return "HumanPlayer(%s, %d)" % (
                    self.userName, self.score)
        else:
            return "BotPlayer(%s, %d, %s, %d)" % (
                    self.userName, self.score, self.botName, self.botVersion)


class GroupContestBotPlayerBean(object):

    def __init__(self, tree):
        self._tree = tree

    @CachedProperty
    def name(self):
        return self._tree.xpath('./a[contains(@class, "botname")]')[0].text.strip()

    @CachedProperty
    def id(self):
        _onclick = self._tree.xpath('./a[contains(@class, "favorite")]/@onclick')[0]
        return _regexBotIDFromFavorite.match(_onclick).group(1)

    @CachedProperty
    def version(self):
        _version = self._tree.xpath('./a[contains(@class, "botname")]/span[@class="version"]')[0].text
        return int(_version)

    @CachedProperty
    def score(self):
        _score = self._tree.find('./div[1]').text
        return int(_score)

    @CachedProperty
    def user(self):
        return self._tree.xpath('./a[@class="username" or @class="smallusername"]')[0].text

    @CachedProperty
    def userID(self):
        _href = self._tree.xpath('./a[@class="username" or @class="smallusername"]/@href')[0]
        return _href.split("/")[-1]

    def __repr__(self):
        return "BotPlayer(%s, %d, %s, %d)" % (
                self.name, self.version, self.score, self.user)
