# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 19:49:49
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-27 22:54:52

__all__ = [

    "ForcedAttackTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...action import Action
from ...strategy.status import Status
from ...strategy.signal import Signal

#{ BEGIN }#

class ForcedAttackTeamDecision(TeamDecisionMaker):
    """
    强攻信号
    ----------------

    为了解决单人决策行为过于保守的问题

    在攻击过程中，一些所谓的有潜在危险的行为，实际上一点危险都没有,但是为了防止出错，就原地等待，
    这反而是贻误了战机，甚至最后还要匆忙转攻为守，实际上根本就防不住

    所以应该根据战场形势分析潜在风险究竟有多大，如果实际上是没有风险的，就发动强攻信号，让攻击者
    保持进攻，而不去过分规避风险

    如下情况是值得发动强攻信号的：
    1. 侵略/僵持模式，出现了停止前进，防止被杀的状况
       - 敌人正在和队友交火，敌人此回合可以射击，但是下回合必定会攻击队友
       - 敌人正在和队友隔墙僵持，敌人可以射击，但是他并不攻击，多半是为了拖延战局
       - 敌人正在和队友重叠，敌人可以射击，但是他一直在等待队友决策
    2. 侵略/僵持模式，出现了停止前进，两方均越过了中线，对方明显不会回头，不想防你

    """
    def _make_decision(self):

        team = self._team
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:
            action = player.get_current_decision()

            if player.has_team_decision() or player.defeated:
                continue

            if (   player.has_status(Status.AGGRESSIVE)  # 侵略模式
                or player.has_status(Status.STALEMENT)   # 僵持模式
                ):
                if (action == Action.STAY # 但是出现了停止前进
                    and player.has_status(Status.WAIT_FOR_MARCHING)    # 等待行军
                    and player.has_status(Status.PREVENT_BEING_KILLED) # 是为了防止被杀
                    ):
                    _shouldForcedMarch = False

                    playerRiskyEnemyBattler = player.get_risky_enemy()
                    if playerRiskyEnemyBattler is None: # 说明是因为没有弹药？
                        continue
                    oppPlayer = Tank2Player(playerRiskyEnemyBattler)
                    teammate = player.teammate # 考虑队友和敌军的情况

                    #debug_print(player.get_risky_enemy())
                    #debug_print(teammate.get_risky_enemy())

                    # 敌人正在和队友交火
                    #------------------
                    # 这种情况直接前进
                    #
                    if (oppPlayer.has_status(Status.ENCOUNT_ENEMY)
                        and oppPlayer.has_status(Status.READY_TO_FIGHT_BACK)
                        and oppPlayer.get_risky_enemy() is teammate.battler
                        ): # 说明对方正准备和队友交火
                        _shouldForcedMarch = True

                    # 敌人正在和队友隔墙僵持
                    #----------------------
                    # 如果他们僵持了超过一回合以上
                    # 保守起见，等待一回合，如果对方并未攻击我，说明它更关心和队友僵持，或者故意在拖时间
                    #
                    # 那么可以直接进攻
                    #
                    elif (oppPlayer.has_status(Status.HAS_ENEMY_BEHIND_BRICK) # 僵持超过一回合
                        and oppPlayer.has_status_in_previous_turns(Status.HAS_ENEMY_BEHIND_BRICK, turns=1)
                        and oppPlayer.get_risky_enemy() is teammate.battler
                        and player.has_status_in_previous_turns(Status.WAIT_FOR_MARCHING, turns=1) # 已经等待了一回合
                        and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1)
                        ):
                        _shouldForcedMarch = True

                    # 敌人正在和队友重叠
                    #----------------------------
                    # 如果他们重叠不动超过一回合以上
                    # 保守起见，等待一回合，如果对方并未攻击我，说明它更关心和队友重叠
                    #
                    # 那么可以直接进
                    #
                    elif (oppPlayer.has_status(Status.OVERLAP_WITH_ENEMY) # 僵持超过一回合
                        and oppPlayer.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                        and player.has_status_in_previous_turns(Status.WAIT_FOR_MARCHING, turns=1) # 已经等待了一回合
                        and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1)
                        ):
                        _shouldForcedMarch = True

                    # 双方均跨过中线
                    #-----------------------------
                    # 那么不再反击，直接进攻？
                    #
                    # TODO:
                    #   存在着一攻一守的 bot
                    #
                    if _shouldForcedMarch: # 建议强制行军

                        with player.create_snapshot() as manager:
                            action3, signal3 = player.make_decision(Signal.FORCED_MARCH)
                            if Signal.is_break(signal3):
                                continue
                            if signal3 == Signal.READY_TO_FORCED_MARCH:
                                returnActions[player.id] = action3
                                player.set_team_decision(action3)
                                manager.discard_snapshot()

        return returnActions

#{ END }#
