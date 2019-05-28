# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 19:35:43
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-28 09:49:47

__all__ = [

    "LeaveTeammateTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...action import Action
from ...strategy.signal import Signal

#{ BEGIN }#

class LeaveTeammateTeamDecision(TeamDecisionMaker):
    """
    和队友打破重叠的团队决策

    己方两个坦克重叠在一起这种事情实在是太愚蠢了 ...

    """
    def _make_decision(self):

        team = self._team
        player1, player2 = team.players
        returnActions = [ player.get_current_decision() for player in team.players ]

        if player1.defeated or player2.defeated: # 有队友已经挂了，那就不需要考虑这个情况了
            return returnActions

        if player1.tank.xy == player2.tank.xy:

            if len([ action for action in returnActions if Action.is_move(action) ]) == 1:
                pass # 一人移动一人非移动，那么是合理的

            elif (
                all( Action.is_move(action) for action in returnActions )
                and returnActions[0] != returnActions[1]
                ): # 两人均为移动，但是两人的移动方向不一样，这样也是可以的
                pass

            elif all([ player.has_team_decision() for player in team.players ]):
                pass # 两者都拥有团队命令

            else:
                # 两个队员可以认为是一样的，因此任意选择一个就好
                if player1.has_team_decision():
                    player, idx = (player2, 1)
                else:
                    player, idx = (player1, 0)

                with player.create_snapshot() as manager:
                    action3, signal3 = player.make_decision(Signal.SHOULD_LEAVE_TEAMMATE)
                    if signal3 == Signal.READY_TO_LEAVE_TEAMMATE:
                        returnActions[idx]  = action3
                        player.set_team_decision(action3)
                        manager.discard_snapshot() # 保存更改

        return returnActions

#{ END }#