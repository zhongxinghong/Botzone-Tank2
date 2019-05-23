# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-23 15:25:39
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 15:55:36

__all__ = [

    "GroupContestBean",

    ]

from lxml import etree
from ..utils import parse_utc_timestamp
from ...utils import CachedProperty
from .match import GroupContestMatchBean
from .player import GroupContestParticipantBean


class GroupContestBean(object):

    def __init__(self, json, game="-"):
        self._json = json  # contest_detail
        self._game = game  # game name

    @CachedProperty
    def _tree(self):
        return etree.HTML(self._json["table"])

    @property
    def game(self):
        return self._game

    @CachedProperty
    def name(self):
        return self._json["contest"]["name"]

    @CachedProperty
    def description(self):
        return self._json["contest"]["desc"]

    @CachedProperty
    def id(self):
        return self._json["contest"]["_id"]

    @CachedProperty
    def group(self):
        return self._json["contest"]["group"]["name"]

    @CachedProperty
    def groupID(self):
        return self._json["contest"]["group"]["_id"]

    @CachedProperty
    def time(self):
        utc = self._json["contest"]["start_time"]
        return parse_utc_timestamp(utc).timestamp()

    @CachedProperty
    def status(self):
        return self._json["status"]

    @CachedProperty
    def players(self):
        return [ GroupContestParticipantBean(data) for data in self._json["contest"]["players"] ]

    @CachedProperty
    def matches(self):
        tree = self._tree
        return [ GroupContestMatchBean(tr, self) for tr in tree.xpath(".//tr") ]

    def __repr__(self):
        return "Contest(%s, %s)" % (
                self.name, self.group)