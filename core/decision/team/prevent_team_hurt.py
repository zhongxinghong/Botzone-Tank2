# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 20:36:28
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-28 01:09:58

__all__ = [

    "PreventTeamHurtTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...action import Action
from ...strategy.status import Status

#{ BEGIN }#

class PreventTeamHurtTeamDecision(TeamDecisionMaker):
    """
    防止队员自残
    --------------
    在决策链的最后，判断是否出现队友恰好打掉准备移动的队友的情况，并加以协调

    """
    def _make_decision(self):

        team = self._team
        map_ = team._map
        oppBase = map_.bases[1 - team.side]
        player1, player2 = team.players
        returnActions = [ player.get_current_decision() for player in team.players ]

        if player1.defeated or player2.defeated: # 有队友已经挂了，没必要考虑这个情况
            return returnActions

        action1, action2 = returnActions
        _mayShouldForcedStop = False

        if Action.is_shoot(action1) and Action.is_move(action2):
            shootAction = action1
            shootPlayer = player1
            moveAction  = action2
            movePlayer  = player2
            _mayShouldForcedStop = True
        elif Action.is_move(action1) and Action.is_shoot(action2):
            shootAction = action2
            shootPlayer = player2
            moveAction  = action1
            movePlayer  = player1
            _mayShouldForcedStop = True

        if _mayShouldForcedStop:
            moveBattler = movePlayer.battler
            shootBattler = shootPlayer.battler
            _shouldForcedStop = False
            with map_.simulate_one_action(moveBattler, moveAction):
                with map_.simulate_one_action(shootBattler, shootAction):
                    if moveBattler.destroyed: # 刚好把队友打死 ...
                        _shouldForcedStop = True

            if _shouldForcedStop:
                #
                # TODO:
                #   如何决策？
                #   改动射击和决策都有可能很危险
                #

                #
                # 这里先做一个特殊情况，那就是重叠攻击基地，这种情况将移动的队友视为不移动
                #
                # TODO:
                #   好吧，这种情况和主动和队友打破重叠的行为是相斥的 ...
                #
                '''if (moveBattler.xy == shootBattler.xy
                    and moveBattler.is_face_to_enemy_base(ignore_brick=False)
                    and shootBattler.is_face_to_enemy_base(ignore_brick=False)
                    ):
                    returnActions[movePlayer.id] = Action.STAY
                    hasTeamActions[movePlayer.id] = True'''


                #
                # 先判断这种情况 5ce92f70d2337e01c7abf587
                #-----------------
                #

                # 默认让射击队友停下
                #--------------------
                stayID = shootBattler.id
                stopPlayer = shootPlayer

                #
                # 以下情况，应该让 moveBattler 停下来
                #
                # 1. 射击队友正在和敌人对射
                # 2. 射击队员正面向敌人基地（为了触发团队协作）
                #
                # 其他更有待补充 ...
                #
                if (shootPlayer.has_status(Status.READY_TO_FIGHT_BACK)
                    or shootPlayer.battler.on_the_same_line_with(oppBase, ignore_brick=True)
                    ):
                    stayID = moveBattler.id
                    stopPlayer = movePlayer

                stopPlayer.set_status(Status.FORCED_STOP_TO_PREVENT_TEAM_HURT)
                returnActions[stayID] = Action.STAY
                stopPlayer.set_current_decision(Action.STAY)
                stopPlayer.set_team_decision(Action.STAY)


        return returnActions

#{ END }#