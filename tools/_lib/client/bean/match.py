# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 16:54:33
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-05 20:01:18

__all__ = [

    "MatchBean",

    ]

from ...utils import CachedProperty
from ..const import BOTZONE_URL_MATCH
from ..utils import parse_utc_timestamp
from .player import BotPlayerBean


class MatchBean(object):

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
        return [ BotPlayerBean(player) for player in self._json["players"] ]

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