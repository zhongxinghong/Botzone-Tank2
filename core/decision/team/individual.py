# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 19:22:17
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-27 20:01:48

__all__ = [

    "IndividualTeamDecision",

    ]

from ..abstract import TeamDecisionMaker

#{ BEGIN }#

class IndividualTeamDecision(TeamDecisionMaker):
    """
    两人分别单独地进行决策，团队决策的起点

    """
    def _make_decision(self):

        team = self._team
        player1, player2 = team.players

        action1, _ = player1.make_decision()
        action2, _ = player2.make_decision()

        return [ action1, action2 ]

#{ END }#