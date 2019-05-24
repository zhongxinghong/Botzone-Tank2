# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 17:02:55
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 18:59:29

__all__ = [

    "RankBotPlayerBean",
    "GroupContestParticipantBean",
    "FavoriteMatchBotPlayerBean",
    "FavoriteMatchBrowserPlayerBean",
    "GlobalMatchPlayerBean",
    "GroupContestBotPlayerBean",

    ]

import re
from ...utils import CachedProperty


_regexBotIDFromFavorite = re.compile(r'AddFavoriteBot\(this,\s*\'(\S+?)\',\s*(?:\d+)\)')


class AbstractPlayerBean(object):

    def __init__(self, *args, **kwargs):
        if __class__ is self.__class__:
            raise NotImplementedError

    @property
    def isBot(self):
        raise NotImplementedError

    def _raise_if_not_a_bot(self):
        if not self.isBot:
            raise Exception("I'm not a bot player")

    @property
    def userName(self):
        raise NotImplementedError

    @property
    def userID(self):
        raise NotImplementedError


class RankBotPlayerBean(AbstractPlayerBean):

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

    @property
    def isBot(self):
        return True

    def __repr__(self):
        return "BotPlayer(%s, %s)" % (
                self.botName, self.userName)

class GroupContestParticipantBean(RankBotPlayerBean):
    pass


class FavoriteMatchBotPlayerBean(RankBotPlayerBean):
    pass


class FavoriteMatchBrowserPlayerBean(AbstractPlayerBean):

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
        return self._json["user"]["name"]

    @CachedProperty
    def userID(self):
        return self._json["user"]["_id"]

    @property
    def isBot(self):
        return False

    def __repr__(self):
        return "BrowserPlayer(%s)" % (self.userName)


class GlobalMatchPlayerBean(AbstractPlayerBean):

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

    def __repr__(self):
        if not self.isBot:
            return "HumanPlayer(%s, %d)" % (
                    self.userName, self.score)
        else:
            return "BotPlayer(%s, %d, %s, %d)" % (
                    self.userName, self.score, self.botName, self.botVersion)


class GroupContestBotPlayerBean(AbstractPlayerBean):

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
    def userName(self):
        return self._tree.xpath('./a[@class="username" or @class="smallusername"]')[0].text

    @CachedProperty
    def userID(self):
        _href = self._tree.xpath('./a[@class="username" or @class="smallusername"]/@href')[0]
        return _href.split("/")[-1]

    @CachedProperty
    def isBot(self):
        return True

    def __repr__(self):
        return "BotPlayer(%s, %d, %s, %d)" % (
                self.name, self.version, self.score, self.userName)
