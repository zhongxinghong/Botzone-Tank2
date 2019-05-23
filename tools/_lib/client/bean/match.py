# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 16:54:33
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 15:57:51

__all__ = [

    "RankMatchBean",
    "GlobalMatchBean",
    "GroupContestMatchBean",

    ]

from ...utils import CachedProperty
from ..const import BOTZONE_URL_MATCH
from ..utils import parse_timestamp, parse_utc_timestamp
from .player import RankBotPlayerBean, GlobalMatchPlayerBean, GroupContestBotPlayerBean


class RankMatchBean(object):

    def __init__(self, json):
        self._json = json

    @CachedProperty
    def id(self):
        return self._json["_id"]

    @CachedProperty
    def time(self):
        utc = self._json["create_time"]
        return parse_utc_timestamp(utc).timestamp()

    @CachedProperty
    def game(self):
        return self._json["game"]["name"]

    @CachedProperty
    def scores(self):
        return self._json["scores"]

    @CachedProperty
    def players(self):
        return [ RankBotPlayerBean(player) for player in self._json["players"] ]

    @CachedProperty
    def url(self):
        return BOTZONE_URL_MATCH.format(matchID=self.id)

    def __repr__(self):
        return "Match(%s, %d, %d, %s, %s)" % (
                self.game, self.scores[0], self.scores[1],
                self.players[0].botName, self.players[1].botName)

    @CachedProperty
    def dict(self):
        return {
            "id": self.id,
            "game": self.game,
            "time": self.time,
            "scores": self.scores,
            "players": [ (player.botName, player.userName) for player in self.players ],
            "url": self.url,
            }

'''
JSON sample:

{
    "scores": [1, 1],
    "_id": "5cce9c5da51e681f0e8e2922",
    "players": [
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
    },
    {
        "_id": "5cce9c5da51e681f0e8e2924",
        "type": "bot",
        "bot":
        {
            "_id": "5ccd3fb0a51e681f0e8d05a9",
            "ver": 34,
            "bot":
            {
                "score": 1211.4479868269364,
                "opensource": false,
                "ranked": true,
                "_id": "5cc70d6275e55951524caa17",
                "name": "另一个垃圾bot"
            },
            "user":
            {
                "_id": "5cc0549c35f461309c28197e",
                "name": "rabbit"
            }
        }
    }],
    "create_time": "2019-05-05T08:18:37.576Z",
    "game":
    {
        "_id": "5c908e0e7857b210f901be7d",
        "name": "Tank2"
    }
}
'''


class GlobalMatchBean(object):

    def __init__(self, tree):
        self._tree = tree  # lxml.etree._Element  from etree.HTML(r.content)

    @CachedProperty
    def id(self):
        return self._tree.xpath('./td[5]/a/@href')[0].split("/")[-1]

    @CachedProperty
    def time(self):
        _timestamp = self._tree.find('./td[1]').text
        return parse_timestamp(_timestamp).timestamp()

    @CachedProperty
    def game(self):
        return self._tree.find('./td[2]/a').text

    @CachedProperty
    def scores(self):
        return [ player.score for player in self.players ]

    @CachedProperty
    def players(self):
        _divs = self._tree.xpath('./td[4]/div[contains(@class, "matchresult")]')
        return [ GlobalMatchPlayerBean(div) for div in _divs ]

    @CachedProperty
    def url(self):
        return BOTZONE_URL_MATCH.format(matchID=self.id)


    def __repr__(self):
        _players = [ (player.botName, player.userName) if player.isBot else player.userName
                        for player in self.players ]
        return "Match(%s, %d, %d, %s, %s)" % (
                self.game, self.scores[0], self.scores[1],
                _players[0], _players[1])

    @CachedProperty
    def dict(self):
        return {
            "id": self.id,
            "game": self.game,
            "time": self.time,
            "scores": self.scores,
            "players": [ (player.botName if player.isBot else None, player.userName)
                            for player in self.players ],
            "url": self.url,
            }



class GlobalMatchBean(object):

    def __init__(self, tree):
        self._tree = tree  # lxml.etree._Element  from etree.HTML(r.content)

    @CachedProperty
    def id(self):
        return self._tree.xpath('./td[5]/a/@href')[0].split("/")[-1]

    @CachedProperty
    def time(self):
        _timestamp = self._tree.find('./td[1]').text
        return parse_timestamp(_timestamp).timestamp()

    @CachedProperty
    def game(self):
        return self._tree.find('./td[2]/a').text

    @CachedProperty
    def scores(self):
        return [ player.score for player in self.players ]

    @CachedProperty
    def players(self):
        _divs = self._tree.xpath('./td[4]/div[contains(@class, "matchresult")]')
        return [ GlobalMatchPlayerBean(div) for div in _divs ]

    @CachedProperty
    def url(self):
        return BOTZONE_URL_MATCH.format(matchID=self.id)


    def __repr__(self):
        _players = [ (player.botName, player.userName) if player.isBot else player.userName
                        for player in self.players ]
        return "Match(%s, %d, %d, %s, %s)" % (
                self.game, self.scores[0], self.scores[1],
                _players[0], _players[1])

    @CachedProperty
    def dict(self):
        return {
            "id": self.id,
            "game": self.game,
            "time": self.time,
            "scores": self.scores,
            "players": [ (player.botName if player.isBot else None, player.userName)
                            for player in self.players ],
            "url": self.url,
            }



class GroupContestMatchBean(object):

    def __init__(self, tree, contest):
        self._tree = tree       # lxml.etree._Element
        self._contest = contest # ContestBean

    @CachedProperty
    def id(self):
        return self._tree.xpath('./td[4]/a/@href')[0].split("/")[-1]

    @property
    def contestID(self):
        return self._contest.id

    @property
    def groupID(self):
        return self._contest.groupID

    @property
    def contest(self):
        return self._contest.name

    @property
    def group(self):
        return self._contest.group

    @CachedProperty
    def time(self):
        _timestamp = self._tree.find('./td[1]').text
        return parse_timestamp(_timestamp).timestamp()

    @property
    def game(self):
        return self._contest.game

    @CachedProperty
    def scores(self):
        return [ player.score for player in self.players ]

    @CachedProperty
    def players(self):
        _divs = self._tree.xpath('./td[3]/div[contains(@class, "matchresult")]')
        return [ GroupContestBotPlayerBean(div) for div in _divs ]

    @CachedProperty
    def url(self):
        return BOTZONE_URL_MATCH.format(matchID=self.id)


    def __repr__(self):
        _players = [ (player.name, player.user) for player in self.players ]
        return "Match(%s, %d, %d, %s, %s)" % (
                self.game, self.scores[0], self.scores[1],
                _players[0], _players[1])

    @CachedProperty
    def dict(self):
        return {
            "id": self.id,
            "game": self.game,
            "contest": self.contest,
            "group": self.group,
            "time": self.time,
            "scores": self.scores,
            "players": [ (player.name, player.user) for player in self.players ],
            "url": self.url,
            }