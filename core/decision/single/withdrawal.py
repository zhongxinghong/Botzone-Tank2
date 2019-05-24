# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-24 10:29:31
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 17:04:50

__all__ = [

    "WithdrawalDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...global_ import np
from ...utils import outer_label, debug_print, debug_pprint
from ...action import Action
from ...strategy.evaluate import evaluate_aggressive, estimate_route_blocking
from ...strategy.status import Status
from ...strategy.label import Label

#{ BEGIN }#

class WithdrawalDecision(SingleDecisionMaker):
    """
    主动回撤逻辑
    -------------
    如果我方大逆风，那么主动回防基地

    具有一个持久性的记忆标签 KEEP_ON_WITHDRAWING

    带有这个标签的 player 在决策的时候，比 WithdrawalDecision 优先级高的决策应该以
    WITHDRAW 状态为优先

    带有 WITHDRAW 持久标记的 player 决策必定会在此处终止，否则就要取消这个标记和状态，
    让后续的决策继续进行

    """
    def _make_decision(self):

        player  = self._player
        signal  = self._signal
        map_    = player._map
        battler = player.battler
        base    = map_.bases[battler.side]
        x2, y2  = base.xy

        Tank2Player = type(player)
        BattleTank  = type(battler)

        oppTank = battler.get_nearest_enemy()
        oppBattler = BattleTank(oppTank)
        oppPlayer = Tank2Player(oppBattler)

        status = evaluate_aggressive(battler, oppBattler)

        #
        # 首先，检查带有持久化 WITHDRAW 标签的 player
        # 该回合是否还需要真正的延续这个标签
        #
        if (player.has_label(Label.KEEP_ON_WITHDRAWING)
            and status != Status.WITHDRAW  # 实际评估不是 WITHDRAW
            ):
            strictStatus = evaluate_aggressive(battler, oppBattler, strict=True)
            if strictStatus == Status.AGGRESSIVE: # 假如对方上回合被击杀，那么我方大概率会触发侵略模式？
                player.remove_status(Status.WITHDRAW)
                player.remove_labels(Label.KEEP_ON_WITHDRAWING)
                player.set_status(status)
                return # 留给其他 decision 处理

        if status == Status.WITHDRAW or player.has_status(Status.WITHDRAW):

            player.remove_labels(Status.AGGRESSIVE, Status.DEFENSIVE, Status.STALEMENT)
            player.set_status(Status.WITHDRAW)
            player.add_labels(Label.KEEP_ON_WITHDRAWING) # 这个状态一旦出现，就添加标记

            #
            # (inserted) 如果上回合已经到达基地附近，那么优先移动到基地对角线的位置等待
            #
            if battler.is_closest_to(base):
                player.set_status(Status.STAY_FOR_GUARDING_OUR_BASE) # 设置为等待
                if (battler.on_the_same_line_with(base) # 和我方基地处在同一直线上，尝试移动到对角线
                    and not player.has_status(Status.BLOCK_ROAD_FOR_OUR_BASE) # 高优先级触发
                    ):
                    for action in battler.get_all_valid_actions():
                        realAction = player.try_make_decision(action)
                        if not Action.is_stay(realAction):
                            if Action.is_shoot(realAction):
                                destroyedFields = battler.get_destroyed_fields_if_shoot(realAction)
                                if len(destroyedFields) == 0:
                                    continue
                                for field in destroyedFields:
                                    if field is base: # 不能拆了自己家
                                        continue
                                    x1, y1 = field.xy
                                    if np.abs(x1 - x2) <= 1 and np.abs(y1 - y2) <= 1:
                                        return realAction
                                else:
                                    continue
                            else:
                                # 否则就是移动了
                                with map_.simulate_one_action(battler, realAction):
                                    if battler.is_closest_to(base): # 模拟一步后仍然保持在基地附近
                                        return realAction

                return Action.STAY # 其他情况下继续等待

            _route1 = battler.get_shortest_defensive_route()
            _route2 = oppBattler.get_shortest_attacking_route()        # 如果不将我视为钢墙
            _route3 = oppBattler.get_shortest_attacking_route(
                            ignore_enemies=False, bypass_enemies=True) # 如果将我视为钢墙

            # TODO:
            #   如果 route2 和 route3 距离差很大，那么可以选择不动
            #
            if _route2.is_not_found() or _route3.is_not_found(): # 对方找不到进攻路线，那就相当于我方把路堵住了？
                return Action.STAY

            assert not _route1.is_not_found() # 这个不可能的吧

            allowedDelay = _route2.length - (_route1.length - 2) # 我方防御路线比地方进攻路线领先值
            allowedDelay -= 1  # 至少要快一步
            if allowedDelay < 0:
                allowedDelay = 0

            returnAction = Action.INVALID
            with outer_label() as OUTER_BREAK:
                for route in sorted( battler.get_all_shortest_defensive_routes(delay=allowedDelay),
                                        key=lambda route: estimate_route_blocking(route) ): # 阻塞程度最小的优先

                    action = battler.get_next_defensive_action(route)
                    realAction = player.try_make_decision(action)

                    if Action.is_stay(realAction):
                        if battler.is_closest_to(base):
                            returnAction = realAction
                            raise OUTER_BREAK
                        else:
                            continue  # 尽量找移动的行为
                    else:
                        returnAction = realAction
                        raise OUTER_BREAK

            if not Action.is_valid(returnAction): # 没有一个合适的行为？
                action = battler.get_next_defensive_action(_route1) # 那就随便来一个把 ...
                returnAction = player.try_make_decision(action)

            if Action.is_move(returnAction) or Action.is_shoot(returnAction):
                player.set_status(Status.READY_TO_WITHDRAW)
            else: # stay
                if battler.is_closest_to(base):
                    player.set_status(Status.STAY_FOR_GUARDING_OUR_BASE)
                else:
                    if player.get_risky_enemy() is not None: # 存在风险敌人就能判定是因为敌人阻挡？
                        player.set_status(Status.WAIT_FOR_WITHDRAWING)
                        player.set_status(Status.PREVENT_BEING_KILLED)

            return returnAction

#{ END }#
