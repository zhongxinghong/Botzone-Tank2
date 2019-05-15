# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 17:46:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-15 18:03:36

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
    """
    def _make_decision(self):

        player      = self._player
        Tank2Player = type(player)

        signal  = self._signal
        map_    = player._map
        tank    = player.tank
        battler = player.battler


        # (inserted) 主动打破重叠的信号
        #------------------------------
        # 1. 如果是侵略模式，则主动前进/射击
        # 2. 如果是防御模式，则主动后退
        # 3. 如果是僵持模式？ 暂时用主动防御逻辑
        #       TODO:
        #           因为还没有写出强攻信号，主动攻击多半会失败 ...
        #
        if signal == Signal.SUGGEST_TO_BREAK_OVERLAP:
            player.set_status(Status.ENCOUNT_ENEMY)
            player.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)
            oppPlayer = Tank2Player(oppBattler)
            status = evaluate_aggressive(battler, oppBattler)
            player.set_status(status)
            if status == Status.AGGRESSIVE: # 只有侵略模式才前进
                action = battler.get_next_attack_action()
                if Action.is_shoot(action): # 能触发这个信号，保证能射击
                    player.set_status(Status.READY_TO_BREAK_OVERLAP)
                    player.set_status(Status.KEEP_ON_MARCHING)
                    return ( action, Signal.READY_TO_BREAK_OVERLAP )
                elif Action.is_move(action): # 专门为这个情况写安全性测试
                    if player.is_safe_to_break_overlap_by_movement(action, oppBattler):
                        # 没有风险，且已知这个移动是符合地图情况的
                        player.set_status(Status.READY_TO_BREAK_OVERLAP)
                        player.set_status(Status.KEEP_ON_MARCHING)
                        return ( action, Signal.READY_TO_BREAK_OVERLAP )
                    else:
                        pass # 这个位置漏下去，让 DEFENSIVE 模式的逻辑继续处理
                        #player.set_status(Status.KEEP_ON_OVERLAPPING) # 继续保持状态
                        #return ( Action.STAY, Signal.CANHANDLED )

                else: # 只能等待？ 注定不会到达这里
                    player.set_status(Status.KEEP_ON_OVERLAPPING) # 继续保持状态
                    return ( Action.STAY, Signal.CANHANDLED )

            #　非侵略模式，或者侵略模式想要前进但是不安全，那么就往后退堵路
            #------------------------
            # 为了防止这种情况的发生 5cd356e5a51e681f0e921453
            #
            # 这里不只思考默认的最优路径，而是将所有可能的最优路径都列举出来
            # 因为默认的最优路径有可能是破墙，在这种情况下我方坦克就不会打破重叠
            # 这就有可能错失防御机会
            #
            # 当然还要注意这种一直跟随和被拖着打的情况 5cd3f56d86d50d05a0083621 / 5ccec5a6a51e681f0e8e46c2
            #
            for enemyAttackRoute in oppBattler.get_all_shortest_attacking_routes():

                oppAction = oppBattler.get_next_attack_action(enemyAttackRoute) # 模拟对方的侵略性算法
                if Action.is_move(oppAction) or Action.is_shoot(oppAction): # 大概率是移动
                    # 主要是为了确定方向
                    oppAction %= 4
                    #
                    # 先处理对方跟随我的情况
                    #--------------------------
                    # 上回合试图通过移动和对方打破重叠，但是现在还在重叠
                    # 说明对方跟着我走了一个回合
                    #
                    if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                        and Action.is_move(player.get_previous_action(back=1))
                        ):
                        oppPlayer.add_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY)


                    if (oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY) # 带有同时打破重叠标记的敌人
                        and battler.canShoot # 这回合可以射击，则改为射击
                        ):
                        player.set_status(Status.READY_TO_BREAK_OVERLAP,
                                        Status.ANTICIPATE_TO_KILL_ENEMY) # 尝试击杀敌军
                        return ( oppAction + 4 , Signal.READY_TO_BREAK_OVERLAP )

                    # 检查是否可以安全打破重叠
                    #--------------------------
                    if player.is_safe_to_break_overlap_by_movement(oppAction, oppBattler):
                        player.set_status(Status.READY_TO_BREAK_OVERLAP)
                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return ( oppAction, Signal.READY_TO_BREAK_OVERLAP )

            else: # 否则选择等待
                player.set_status(Status.KEEP_ON_OVERLAPPING)
                return ( Action.STAY, Signal.CANHANDLED )


        # 与敌人重合时，一般只与一架坦克重叠
        #--------------------------
        # 1. 根据路线评估侵略性，确定采用进攻策略还是防守策略
        # 2.
        #
        if battler.has_overlapping_enemy():
            player.set_status(Status.ENCOUNT_ENEMY)
            player.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)
            oppPlayer = Tank2Player(oppBattler)

            # 评估进攻路线长度，以确定采用保守策略还是入侵策略
            status = evaluate_aggressive(battler, oppBattler)
            player.set_status(status)

            # 侵略模式
            #-----------
            # 1. 直奔对方基地，有机会就甩掉敌人
            #
            if status == Status.AGGRESSIVE:
                if not oppBattler.canShoot: # 对方不能射击，对自己没有风险
                    # 尝试继续行军
                    action = battler.get_next_attack_action()
                    if Action.is_move(action): # 下一步预计移动
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
                        player.set_status(Status.KEEP_ON_OVERLAPPING) # 可能触发 Signal.SUGGEST_TO_BREAK_OVERLAP
                        return Action.STAY
                else:
                    # TODO: 根据历史记录分析，看看是否应该打破僵局
                    return Action.STAY # 原地等待

            # 防御模式
            #------------
            # 1. 尝试回退堵路
            # 2. 不行就一直等待
            #   # TODO:
            #       还需要根据战场形势分析 ...
            #
            #elif status == DEFENSIVE_STATUS:
            else:
                # 先检查对方上回合是否在跟随我移动
                #-------------------------------
                if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                    and Action.is_move(player.get_previous_action(back=1))
                    ):
                    oppPlayer.add_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY)

                if not oppBattler.canShoot: # 对方不能射击，对自己没有风险，那么就回头堵路！
                    #
                    # 假设对方采用相同的侵略性算法
                    #
                    oppAction = oppBattler.get_next_attack_action()
                    if Action.is_move(oppAction): # 大概率是移动

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
                            player.set_status(Status.READY_TO_BLOCK_ROAD) # 认为在堵路
                            return oppAction

                # 否则等待
                player.set_status(Status.READY_TO_BLOCK_ROAD)
                return Action.STAY

            # 僵持模式
            #------------
            #elif status == STALEMATE_STATUS:
            #    raise NotImplementedError

            # TODO:
            #   more strategy ?
            #
            #   - 追击？
            #   - 敌方基地在眼前还可以特殊处理，比如没有炮弹默认闪避


#{ END }#