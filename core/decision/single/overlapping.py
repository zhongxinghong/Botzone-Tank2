# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 17:46:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-22 08:31:54

__all__ = [

    "OverlappingDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...utils import debug_print
from ...action import Action
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

        player  = self._player
        signal  = self._signal
        map_    = player._map
        tank    = player.tank
        battler = player.battler

        Tank2Player = type(player)
        BattleTank  = type(battler)

        if battler.has_overlapping_enemy():

            player.set_status(Status.ENCOUNT_ENEMY)
            player.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)
            oppPlayer = Tank2Player(oppBattler)

            status = evaluate_aggressive(battler, oppBattler)
            player.set_status(status)

            #
            # 先检查对方上回合是否在跟随我移动，以及时切换决策模式 ...
            #   5cd3f56d86d50d05a0083621 / 5ccec5a6a51e681f0e8e46c2 / 5ce26520d2337e01c7a3ca2b
            #-------------------------------
            if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                and Action.is_move(player.get_previous_action(back=1))
                ):
                oppPlayer.add_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY)

            if (oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY)
                and player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=3)
                and all( Action.is_stay(player.get_previous_action(_back)) for _back in range(1, 3+1) )
                ): # 如果和一个带有 stay 标记的敌人僵持超过 3 回合，就把这个标记移除，因为它此时已经不是一个会和我马上打破重叠的敌人了
                oppPlayer.remove_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY) # 5ce3c990d2337e01c7a54b4c

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
                            #
                            # 首先先处理主动打破重叠的情况的情况
                            # 该情况下会改用定制的安全性测试函数判断情况
                            #
                            # TODO:
                            #   优先尝试不往上回合已经移动过的方向移动 5ce26520d2337e01c7a3ca2b
                            #
                            realAction = action

                            #
                            # 如果遇到和我打破重叠时机一致的对手
                            #-------------------
                            # 1. 尝试换一个方向移动
                            # 2. 如果不能换方向，那么可能在狭道内，那么退回原来的位置，
                            #    这意味着如果敌人下回合开炮，那么他必死 5ce264c2d2337e01c7a3c9f6
                            #
                            if oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY):
                                #
                                # 禁止的行为不一定是反向！因为可能恰好遇到拐弯 ...
                                # 5ce48707d2337e01c7a641b7 / 5ce487a6d2337e01c7a64205
                                #
                                _backTurn = 0
                                previousAction = Action.STAY
                                while Action.is_stay(previousAction): # 有可能上回合是等待，也就是
                                    _backTurn += 1  # 上回合又下方决策得到，因此需要一直回查到移动行为
                                    previousAction = player.get_previous_action(back=_backTurn)

                                forbiddenAction = action
                                revertMoveAction = (previousAction + 2) % 4  # 反向移动的行为
                                #
                                # 尝试移向其他的方向
                                #
                                # TODO:
                                #   太难判断了，还是暂时先禁止把 ... 鬼知道对面怎么算的距离
                                #
                                '''if realAction == forbiddenAction:
                                    route1 = battler.get_shortest_attacking_route()
                                    for optionalAction in battler.get_all_valid_move_action():
                                        if (optionalAction == forbiddenAction
                                            or optionalAction == revertMoveAction # 不要回头
                                            ):
                                            continue
                                        with map_.simulate_one_action(battler, optionalAction):
                                            route2 = battler.get_shortest_attacking_route()
                                            if route2.length <= route1.length: # 移动后不增加攻击距离s
                                                realAction = optionalAction
                                                break'''

                                #
                                # 尝试反向移动
                                #
                                # TODO:
                                #   事实上反向移动也不一定是正确的，因为每一个人对于这种情况的判断是不一样的
                                #   5ce4943ed2337e01c7a64cdd
                                #
                                '''if realAction == forbiddenAction:
                                    with map_.simulate_one_action(battler, revertMoveAction):
                                        if len(oppBattler.try_dodge(battler)) == 0: # 如果这回合他反向射击，那么必死
                                            realAction = revertMoveAction'''

                                #
                                # 否则等待，让敌人开一炮，这样下回合还会继续触发移动
                                # 有可能换一个敌方就可以有别的决策方法
                                # 也有可能直接带到基地 5ce48b77d2337e01c7a644e5
                                #
                                if realAction == forbiddenAction:
                                    player.set_status(Status.OVERLAP_WITH_ENEMY) # 保持等待状况
                                    return Action.STAY


                            if player.is_safe_to_break_overlap_by_movement(realAction, oppBattler):
                                player.set_status(Status.READY_TO_BREAK_OVERLAP)
                                player.set_status(Status.KEEP_ON_MARCHING)
                                return realAction
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