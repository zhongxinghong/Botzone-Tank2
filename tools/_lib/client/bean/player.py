# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-05 17:02:55
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 17:28:59

__all__ = [

    "BotPlayerBean",

    ]

from ...utils import CachedProperty


class BotPlayerBean(object):

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