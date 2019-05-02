# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 01:01:30
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-02 06:11:12
"""
游戏团队类，封装两个 tank 进行共同决策

"""
__all__ = [

    "Tank2Team",

    ]

from .action import Action
from .strategy.signal import Signal

#{ BEGIN }#

class Team(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
        raise NotImplementedError


class Tank2Team(Team):

    def __init__(self, side, player1, player2):
        player1.set_team(self)
        player2.set_team(self)
        self._side = side
        self._player1 = player1
        self._player2 = player2
        self._opponentTeam = None

    @property
    def side(self):
        return self._side

    def set_opponent_team(self, team):
        """
        设置对手团队

        Input:
            - team    Tank2Team
        """
        assert isinstance(team, self.__class__)
        self._opponentTeam = team

    def make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """
        action1 = action2 = Action.INVALID
        signal1 = signal2 = Signal.NONE

        while True:

            action1, signal1 = self._player1.make_decision()
            action2, signal2 = self._player2.make_decision()

            if signal1 == Signal.NONE and signal2 == Signal.NONE:
                break

        # TODO:
        # ------------
        #   团队策略 !!!

        if action1 == Action.INVALID:
            action1 = Action.STAY
        if action2 == Action.INVALID:
            action2 = Action.STAY
        return [ action1, action2 ]

#{ END }#
