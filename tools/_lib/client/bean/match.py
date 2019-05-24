# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 16:54:33
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 19:20:13

__all__ = [

    "RankMatchBean",
    "FavoriteMatchBean",
    "GlobalMatchBean",
    "GroupContestMatchBean",

    ]

from ...utils import CachedProperty
from ..const import BOTZONE_URL_MATCH
from ..utils import parse_timestamp, parse_utc_timestamp
from .player import RankBotPlayerBean, GlobalMatchPlayerBean, GroupContestBotPlayerBean,\
    FavoriteMatchBotPlayerBean, FavoriteMatchBrowserPlayerBean


class AbstractMatchBean(object):

    def __init__(self):
        if __class__ is self.__class__:
            raise NotImplementedError

    @property
    def id(self):
        raise NotImplementedError

    @property
    def time(self): # -> float
        raise NotImplementedError

    @property
    def game(self): # -> str
        raise NotImplementedError

    @property
    def scores(self): # -> [int, int]
        raise NotImplementedError

    @property
    def players(self): # -> [PlayerBean, PlayerBean]
        raise NotImplementedError

    @CachedProperty
    def url(self):
        return BOTZONE_URL_MATCH.format(matchID=self.id)

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

    def __repr__(self):
        _players = [ (player.botName, player.userName) if player.isBot else player.userName
                        for player in self.players ]
        return "Match(%s, %d, %d, %s, %s)" % (
                self.game, self.scores[0], self.scores[1],
                _players[0], _player1[1])


class RankMatchBean(AbstractMatchBean):

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


class FavoriteMatchBean(AbstractMatchBean):

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
        return self._json["scores"] or [-1, -1]  # 比赛可能是没有结束的

    @CachedProperty
    def players(self):
        _players = []
        for data in self._json["players"]:
            _type = data["type"]
            if _type == "bot":
                _players.append(FavoriteMatchBotPlayerBean(data))
            elif _type == "browser":
                _players.append(FavoriteMatchBrowserPlayerBean(data))
            else:
                raise Exception
        return _players


class GlobalMatchBean(AbstractMatchBean):

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


class GroupContestMatchBean(AbstractMatchBean):

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
    def dict(self):
        return {
            "id": self.id,
            "game": self.game,
            "contest": self.contest,
            "group": self.group,
            "time": self.time,
            "scores": self.scores,
            "players": [ (player.name, player.userName) for player in self.players ],
            "url": self.url,
            }
