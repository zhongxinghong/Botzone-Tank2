# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 17:46:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-17 01:57:31

__all__ = [

    "OverlappingDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...action import Action
from ...tank import BattleTank
from ...strategy.status import Status
from ...strategy.signal import Signal
from ...strategy.label import Label
from ...strategy.evaluate import evaluate_aggressive

#{ BEGIN }#

class OverlappingDecision(SingleDecisionMaker):
    """
    与敌人重合时的决策
    ------------------------

    侵略模式
    --------
    1. 直奔对方基地，有机会就甩掉敌人

    防御模式
    --------
    1. 尝试回退堵路
    2. 对于有标记的敌人，考虑采用其他的策略，例如尝试击杀敌军


    多回合僵持后，会有主动打破重叠的决策

    """
    def _make_decision(self):

        player      = self._player
        Tank2Player = type(player)

        signal  = self._signal
        map_    = player._map
        tank    = player.tank
        battler = player.battler


        if battler.has_overlapping_enemy():

            player.set_status(Status.ENCOUNT_ENEMY)
            player.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)
            oppPlayer = Tank2Player(oppBattler)

            status = evaluate_aggressive(battler, oppBattler)
            player.set_status(status)

            # 是否已经有多回合僵持，应该主动打破重叠
            _shouldBreakOverlap = (
                battler.canShoot # 可以射击
                and player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                ) # 上回合重叠这回合还重叠，就视为僵持，趁早打破重叠

            if status == Status.AGGRESSIVE:
                # 对方不能射击，对自己没有风险，或者是符合了主动打破重叠的条件
                if not oppBattler.canShoot or _shouldBreakOverlap:
                    # 尝试继续行军
                    action = battler.get_next_attack_action()
                    if Action.is_move(action):
                        if _shouldBreakOverlap:
                            # 首先先处理主动打破重叠的情况的情况
                            # 该情况下会改用定制的安全性测试函数判断情况
                            if player.is_safe_to_break_overlap_by_movement(action, oppBattler):
                                player.set_status(Status.READY_TO_BREAK_OVERLAP)
                                player.set_status(Status.KEEP_ON_MARCHING)
                                return action
                            else:
                                # 无法安全移动，但是又需要打破重叠，那么就视为防御
                                # 让后续的代码进行处理
                                player.remove_status(Status.AGGRESSIVE)
                                player.set_status(Status.DEFENSIVE)
                                pass # 这里会漏到 DEFENSIVE
                        else:
                            # 开始处理常规情况
                            realAction = player.try_make_decision(action)
                            if Action.is_move(realAction): # 继续起那就
                                player.set_status(Status.KEEP_ON_MARCHING)
                                return realAction
                            # 否则就是等待了，打得更有侵略性一点，可以尝试向同方向开炮！
                            realAction = player.try_make_decision(action + 4)
                            if Action.is_shoot(realAction):
                                player.set_status(Status.KEEP_ON_MARCHING)
                                return realAction

                    elif Action.is_shoot(action): # 下一步预计射击
                        realAction = player.try_make_decision(action)
                        if Action.is_shoot(realAction):
                            player.set_status(Status.KEEP_ON_MARCHING)
                            return realAction
                    else: # 否则停留
                        player.set_status(Status.KEEP_ON_OVERLAPPING)
                        return Action.STAY
                else:
                    player.set_status(Status.KEEP_ON_OVERLAPPING)
                    return Action.STAY # 原地等待


            if status == Status.DEFENSIVE or _shouldBreakOverlap:
                #
                # 先检查对方上回合是否在跟随我移动，因为可能被拖着打 ...
                #   5cd3f56d86d50d05a0083621 / 5ccec5a6a51e681f0e8e46c2
                #-------------------------------
                if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                    and Action.is_move(player.get_previous_action(back=1))
                    ):
                    oppPlayer.add_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY)

                # 对方不能射击，对自己没有风险，或者是符合了主动打破重叠的条件
                if not oppBattler.canShoot or _shouldBreakOverlap:
                    #
                    # 这里不只思考默认的最优路径，而是将所有可能的最优路径都列举出来
                    # 因为默认的最优路径有可能是破墙，在这种情况下我方坦克就不会打破重叠
                    # 这就有可能错失防御机会
                    #
                    for enemyAttackRoute in oppBattler.get_all_shortest_attacking_routes():
                        oppAction = oppBattler.get_next_attack_action(enemyAttackRoute) # 模拟对方的侵略性算法
                        if Action.is_move(oppAction) or Action.is_shoot(oppAction): # 大概率是移动
                            # 主要是为了确定方向
                            oppAction %= 4

                            # 首先先检查对方是否会跟随我，优先击杀
                            #--------------------------
                            if (oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY) # 带有同时打破重叠标记的敌人
                                and battler.canShoot # 这回合可以射击，则改为射击
                                ):
                                player.set_status(Status.READY_TO_BREAK_OVERLAP,
                                                  Status.ANTICIPATE_TO_KILL_ENEMY) # 尝试击杀敌军
                                return ( oppAction + 4 , Signal.READY_TO_BREAK_OVERLAP )

                            # 正常情况下选择堵路
                            #----------------------
                            if player.is_safe_to_break_overlap_by_movement(oppAction, oppBattler): # 模仿敌人的移动方向
                                player.set_status(Status.READY_TO_BREAK_OVERLAP)
                                player.set_status(Status.READY_TO_BLOCK_ROAD) # 认为在堵路
                                return oppAction

                # 否则等待
                player.set_status(Status.READY_TO_BLOCK_ROAD)
                player.set_status(Status.KEEP_ON_OVERLAPPING)
                return Action.STAY


#{ END }#