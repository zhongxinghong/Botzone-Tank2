# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 20:28:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 21:31:02

__all__ = [

    "BackToHelpTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...utils import debug_print
from ...strategy.status import Status
from ...strategy.signal import Signal

#{ BEGIN }#

class BackToHelpTeamDecision(TeamDecisionMaker):
    """
    考虑一种墙后后退的逻辑 5cea650cd2337e01c7ad8de4
    这样可以制造二打一的局面

    TODO:
      回退后可能会造成 WITHDRAW 的情况出现 ?

    """
    def _make_decision(self):

        team = self._team
        map_ = team._map
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:
            action = player.get_current_decision()

            if player.has_team_decision() or player.defeated:
                continue

            teammate = player.teammate
            teammateBattler = teammate.battler
            if (player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)
                and teammate.has_status(Status.WITHDRAW)
                and teammate.has_status(Status.ENCOUNT_ENEMY)
                and (teammate.has_status(Status.READY_TO_FIGHT_BACK)
                    or teammate.has_status_in_previous_turns(Status.READY_TO_FIGHT_BACK, turns=1)
                    ) # 保持对射行为，
                      # TODO:
                      #   或许可以考虑用 对射状态描述撤退状态下的对射？
                ):
                battler = player.battler
                oppBattler = player.get_risky_enemy()
                if oppBattler is None: # 5cee87fc641dd10fdcc91b44 为何空指针 ???
                    continue
                oppPlayer = Tank2Player(oppBattler)
                teammateRiskyEnemyTank = oppPlayer.teammate.tank # 当前和我墙后僵持的敌人的队友
                if oppBattler is not None and teammateRiskyEnemyTank is not None: # 应该不会这样？
                    backAwayAction = battler.back_away_from(oppBattler)
                    _shouldBackAway = False
                    with map_.auto_revert() as counter:
                        while map_.is_valid_move_action(battler, backAwayAction):
                            map_.single_simulate(battler, backAwayAction)
                            counter.increase()
                            if teammateRiskyEnemyTank in battler.get_enemies_around():
                                _shouldBackAway = True
                                break

                    if _shouldBackAway:

                        with player.create_snapshot() as manager:
                            action3, signal3 = player.make_decision(Signal.SUGGEST_TO_BACK_AWAY_FROM_BRICK)
                            if Signal.is_break(signal3):
                                continue

                            if signal3 == Signal.READY_TO_BACK_AWAY_FROM_BRICK:
                                returnActions[player.id] = action3
                                player.set_team_decision(action3)
                                continue

        return returnActions


#{ END }#