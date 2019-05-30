# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 20:04:13
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 20:16:47

__all__ = [

    "BreakBrickTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...action import Action
from ...strategy.status import Status
from ...strategy.signal import Signal

#{ BEGIN }#

class BreakBrickTeamDecision(TeamDecisionMaker):
    """
    主动破墙的团队决策
    -----------------

    乱破墙是不可以的，单人不要随便破墙，但是有条件的破墙是可以的

    """
    def _make_decision(self):

        team = self._team
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:
            action = player.get_current_decision()

            if player.has_team_decision() or player.defeated:
                continue

            if (Action.is_stay(action)                                # 当前回合处于等待状态
                and player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)  # 墙后有人造成的
                and player.has_status(Status.WAIT_FOR_MARCHING)       # 因此等待行军
                #and not player.has_status(Status.DEFENSIVE) # 不要让防御性的队友随意破墙
                and not player.has_status(Status.RELOADING) # 目前有弹药
                # and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=1) # 改成一有机会就先留后路
                ):

                # 触发的条件是一方隔墙，队友因为这两个人的僵持受到牵制
                #----------------------------------------------------

                # 僵持方先破墙，留好后路
                #----------------------
                with player.create_snapshot() as manager:
                    action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_BRICK)
                    if Signal.is_break(signal3):
                        continue

                    if signal3 == Signal.READY_TO_PREPARE_FOR_BREAK_BRICK: # 下一步准备凿墙
                        returnActions[player.id] = action3
                        player.set_team_decision(action3)
                        manager.discard_snapshot()
                        continue # 至此该队员决策完成，等待它这回合凿墙

                    # elif signal3 == Signal.READY_TO_BREAK_BRICK:
                    # 否则将受到破墙信号，开始判断是否符合破墙条件

                    elif signal3 == Signal.READY_TO_BREAK_BRICK:
                        oppBattler = player.get_risky_enemy() # 获得墙后敌人
                        assert oppBattler is not None # 必定有风险敌人
                        oppPlayer = Tank2Player(oppBattler)

                        # playerIdx   = idx
                        # teammateIdx = 1 - idx
                        teammate = player.teammate

                        _shouldBreakBrick = False


                        if oppBattler.has_enemy_around(): # 发现敌人和队友相遇，立即破墙
                            _shouldBreakBrick = True

                        ''' 这个两个触发已经不再需要了 5ce217e8d2337e01c7a3790c

                        # TODO:
                        #   这种情况挺难遇到的，而且一旦遇到一般都为时过晚
                        #   应该要模拟地图预测一下，提前开一炮
                        #
                        if (teammate.has_status(Status.WAIT_FOR_MARCHING) # 队友等待
                            # and self.has_status_in_previous_turns(teammate, Status.WAIT_FOR_MARCHING, turns=1)
                            and teammate.has_status(Status.PREVENT_BEING_KILLED)   # 队友是为了防止被杀
                            ):
                            teammateRiskyEnemyBattler = teammate.get_risky_enemy()
                            playerRiskyEnemyBattler = player.get_risky_enemy() # 墙后敌人
                            if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                # 两者受到同一个敌人牵制，那么发动破墙信号
                                _shouldBreakBrick = True


                        elif ( teammate.has_status(Status.AGGRESSIVE)
                            or teammate.has_status(Status.STALEMENT)
                            ):
                            teammateAction = returnActions[ teammateIdx ]
                            if (Action.is_move(teammateAction) # 确保队友动作为移动
                                and teammate.has_status(Status.KEEP_ON_MARCHING) # 队友正在行军
                                ):
                                # 尝试模拟下一回合的队友状态，并让队友重新决策，查看他的状态
                                with map_.simulate_one_action(teammate, teammateAction):
                                    action4, _ = teammate.make_decision()
                                    if (teammate.has_status(Status.WAIT_FOR_MARCHING)
                                        and teammate.has_status(Status.PREVENT_BEING_KILLED)
                                        ): # 这个时候队友被阻拦
                                        teammateRiskyEnemyBattler = teammate.get_risky_enemy()
                                        playerRiskyEnemyBattler = player.get_risky_enemy()
                                        if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                            _shouldBreakBrick = True # 如果是因为对面墙的坦克在阻拦，那么马上破墙'''

                        #
                        # 如果遇到对手准备和队友对射 5cd364e4a51e681f0e921e7a
                        # 那么考虑直接破墙
                        #
                        # 敌方当前回合应该必定会还击，否则就失去了防御的意义
                        # 于是，随后就会遇到二对一且三方均没有炮弹
                        # 如果对方下回合不走，那么二打一直接干掉
                        # 如果对方下回合移动，那么攻击的队友就解除了威胁，可以继续前进
                        #
                        if (not teammate.has_status(Status.DEFENSIVE)
                            and teammate.has_status(Status.ENCOUNT_ENEMY)
                            and teammate.has_status(Status.READY_TO_FIGHT_BACK)
                            ):
                            teammateRiskyEnemyBattler = teammate.get_risky_enemy()
                            playerRiskyEnemyBattler = player.get_risky_enemy()
                            if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                _shouldBreakBrick = True


                        if _shouldBreakBrick:
                            returnActions[player.id] = action3
                            player.set_team_decision(action3)
                            manager.discard_snapshot()
                            continue


        return returnActions

#{ END }#