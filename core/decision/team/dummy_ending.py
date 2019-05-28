# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-27 16:12:27
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-27 16:25:26

__all__ = [

    "TeamDecisionDummyEnding",

    ]

from ..abstract import TeamDecisionMaker

#{ BEGIN }#

class TeamDecisionDummyEnding(TeamDecisionMaker):
    """
    用于结束 DecisionChain 的结尾

    """
    def is_handled(self, result):
        """
        返回 True ，这样 DecisionChain 就会结束
        """
        return True

    def make_decision(self):
        """
        将 player 缓存的结果直接返回

        """
        team = self._team
        player1, player2 = team.players

        action1 = player1.get_current_decision()
        action2 = player2.get_current_decision()

        return [ action1, action2 ]

#{ END }#
