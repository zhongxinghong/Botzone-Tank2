# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 19:27:16
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-27 21:01:32

__all__ = [

    "VitalTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...strategy.status import Status

#{ BEGIN }#

class VitalTeamDecision(TeamDecisionMaker):
    """
    将关键的个人决策设置为团队决策，个人决策即为团队最优决策，
    低优先级决策者不可对其进行协调

    """
    def _make_decision(self):

        team = self._team

        for player in team.players:
            if (   player.has_status(Status.SACRIFICE_FOR_OUR_BASE)   # 准备为防御基地牺牲
                or player.has_status(Status.BLOCK_ROAD_FOR_OUR_BASE)  # 准备为防御基地堵路
                or player.has_status(Status.READY_TO_ATTACK_BASE)     # 准备攻击敌方基地
                or player.has_status(Status.READY_TO_KILL_ENEMY)      # 准备击杀敌人
                ):
                # TODO: 牺牲攻击局，可能需要考虑一下闪避 5ccca535a51e681f0e8c7131
                action = player.get_current_decision()
                player.set_team_decision(action) # 将个人决策设置为团队决策

        return [ player.get_current_decision() for player in team.players ]

#{ END }#