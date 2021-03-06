# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-24 10:29:31
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 18:23:12

__all__ = [

    "WithdrawalDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...global_ import np
from ...utils import CachedProperty, outer_label, debug_print, debug_pprint
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
    ALLOW_WITHDRAWAL = True  # 一个测试用的 const，设为 False 则取消一切和 WITHDRAW 相关的决策


    @CachedProperty
    def _GUARD_POINTS(self):
        """
        获得基地两个对角线位置的两个防御坐标

        """
        player = self._player
        map_ = player._map
        tank = player.tank
        side = tank.side
        base = map_.bases[side]

        _DIAGONAL_DIRECTIONS = ( (1, 1), (1, -1), (-1, 1), (-1, -1) )

        x1, y1 = base.xy
        points = []
        for dx, dy in _DIAGONAL_DIRECTIONS:
            x2 = x1 + dx
            y2 = y1 + dy
            if map_.in_map(x2, y2):
                points.append( (x2, y2) )

        return points


    def _get_more_dangerous_guard_point(self, oppBattler):
        """
        更加危险的防御点，被认为是距离敌人更近的防御点
        """
        player  = self._player
        battler = player.battler
        _GUARD_POINTS = self._GUARD_POINTS

        distancesToEnemy = [ oppBattler.get_manhattan_distance_to_point(x2, y2)
                                for (x2, y2) in _GUARD_POINTS ]
        return _GUARD_POINTS[ np.argmin(distancesToEnemy) ] # 距离敌人更近的点根据危险性


    def _is_dangerous_action(self, action, oppBattler):
        """
        为了防止出现这样一种情况： 5ce9154fd2337e01c7abd81f
        以及这样一种情况： 5cea5d38d2337e01c7ad8418
        ----------------------------------

        1. 假如我方这回合移动，而敌人下回合通过非射击行为，可以面向我方基地（射击行为的话，下回合对方炮弹冷却，
           对基地暂时不造成威胁），如果我方这回合选择不移动可以阻止它，那么就选择停止

        2. 假如我方这回合射击，而敌人下回合通过非射击行为，可以面向我方基地，那么就选择停止

        3. 假如我方先破一墙，对方出现在后面，那么就算是有威胁

        """
        player  = self._player
        battler = player.battler
        map_    = battler._map

        if (Action.is_move(action)
            and not oppBattler.is_face_to_enemy_base() # 事实上应该不会出现
            ):
            # 先保存所有可能行为，为了防止模拟我方行为后，射击能力被重置
            _shouldStay = False
            enemyAction = Action.STAY
            with map_.simulate_one_action(battler, action):
                for _action in oppBattler.get_all_valid_move_actions() + [ Action.STAY ]:
                    with map_.simulate_one_action(oppBattler, _action):
                        if oppBattler.is_face_to_enemy_base():
                            # 我方执行一步后，对方面对基地
                            _shouldStay = True
                            enemyAction = _action
                            break
            if _shouldStay:
                # 现在不模拟我方行为，然后同样模拟对方行为，看对方是否面对我方基地
                with map_.simulate_one_action(oppBattler, enemyAction):
                    if not oppBattler.is_face_to_enemy_base():
                        return True


        if (Action.is_shoot(action)
            and not oppBattler.is_face_to_enemy_base() # 敌人上回合没有面对我方基地
            ):
            for _action in oppBattler.get_all_valid_move_actions() + [ Action.STAY ]:
                with map_.simulate_one_action(oppBattler, _action):
                    if not oppBattler.is_face_to_enemy_base(): # 当敌人尚未面对我方基地
                        with map_.simulate_one_action(battler, action):
                            if oppBattler.is_face_to_enemy_base(): # 我方射击一步后，敌人面对我方基地
                                return True  # 不安全的

        # 其他情况均认为安全
        return False


    def _try_make_decision(self, action, oppBattler):
        """
        Withdraw 下的 try_make_decision

        """
        player = self._player
        Tank2Player = type(player)
        oppPlayer = Tank2Player(oppBattler)
        realAction = player.try_make_decision(action)

        if (Action.is_stay(realAction)
            and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=2)
            and player.has_status_in_previous_turns(Status.WAIT_FOR_WITHDRAWING, turns=2)
            and not Action.is_shoot(oppPlayer.get_previous_action(back=1))
            and not Action.is_shoot(oppPlayer.get_previous_action(back=2))
            ): # 如果等待了两回合，对方两回合均为射击那么视为安全
            player.set_status(Status.FORCED_WITHDRAW) # 糟糕的设计！如果后续需要更改，那么需要在再删掉这个状态
            realAction = action

        if (Action.is_stay(realAction)
            and not player.has_status(Status.FORCED_WITHDRAW)
            ):
            return Action.STAY

        if self._is_dangerous_action(realAction, oppBattler):
            player.remove_status(Status.FORCED_WITHDRAW)
            return Action.STAY

        return realAction


    def _get_next_action_to_guard_point(self, x2, y2, oppBattler):
        """
        获得趋近守卫点 (x2, y2) 的下一个行为
        """
        player  = self._player
        battler = player.battler
        map_    = player._map
        base    = map_.bases[battler.side]

        route = battler.get_route_to_point_by_move(x2, y2)
        assert not route.is_not_found() # 这个必定能找到路！

        action = battler.get_next_defensive_action(route)
        realAction = self._try_make_decision(action, oppBattler)

        if not Action.is_stay(realAction):
            with map_.simulate_one_action(battler, realAction):
                if not battler.is_closest_to(base):
                    player.remove_status(Status.FORCED_WITHDRAW)
                    return Action.STAY  # 其实是可以确保一直停留在基地附近的？

        return realAction # stay/realAction


    def _make_decision(self):

        if not self.__class__.ALLOW_WITHDRAWAL:
            return self.__class__.UNHANDLED_RESULT

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

        status = evaluate_aggressive(battler, oppBattler, allow_withdraw=self.__class__.ALLOW_WITHDRAWAL)

        #
        # 首先，检查带有持久化 WITHDRAW 标签的 player
        # 该回合是否还需要真正的延续这个标签
        #
        # 一种情况是考虑是否应该
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
        #
        # 一种情况是考虑上回合是否击杀了一个人
        #
        if len([ _oppPlayer for _oppPlayer in player.opponents if _oppPlayer.defeated ]) == 1:
            teammate = player.teammate
            if not teammate.defeated: # 二打一的局势，此时 oppBattler 为剩下一个敌人
                teammateBattler = teammate.battler
                _dontWithdraw = False
                _deltaDistanceToEnemy = battler.get_manhattan_distance_to(oppBattler) - teammateBattler.get_manhattan_distance_to(oppBattler)
                if _deltaDistanceToEnemy > 0: # 我比队友距离更远
                    _dontWithdraw = True
                elif _deltaDistanceToEnemy == 0: # 一样远
                    _deltaDistanceToOurBase = battler.get_manhattan_distance_to(base) - teammateBattler.get_manhattan_distance_to(base)
                    if _deltaDistanceToOurBase > 0: # 我比队友理基地更远，那么让队友防御
                        _dontWithdraw = True
                    elif _deltaDistanceToOurBase == 0: # 如果还是一样远 ...
                        if not teammate.has_label(Label.DONT_WITHDRAW): # 避免两者同时强攻，那么就让先判断的队友进行强攻
                            _dontWithdraw = True

                if _dontWithdraw:
                    player.remove_status(Status.WITHDRAW)
                    player.remove_labels(Label.KEEP_ON_WITHDRAWING)
                    player.add_labels(Label.DONT_WITHDRAW)
                    return # 留给其他 decision 处理


        if status == Status.WITHDRAW or player.has_status(Status.WITHDRAW):

            player.remove_labels(Status.AGGRESSIVE, Status.DEFENSIVE, Status.STALEMENT)
            player.set_status(Status.WITHDRAW)
            player.add_labels(Label.KEEP_ON_WITHDRAWING) # 这个状态一旦出现，就添加标记

            #
            # (inserted) 不要轻易从中线撤退，应该想一下是否可以堵路
            #
            if battler.is_near_midline(offset=2): # y = [2, 6]
                for action in [ Action.STAY ] + battler.get_all_valid_move_actions(): # 先判断 stay
                    with map_.simulate_one_action(battler, action):
                        if battler.can_block_this_enemy(oppBattler):
                            player.set_status(Status.READY_TO_BLOCK_ROAD)
                            return action  # 不需要判断安全性？

            #
            # 1. 如果上回合已经到达基地附近，那么优先移动到基地对角线的位置等待
            # 2. 必要时改变守卫的位置
            #
            # TODO:
            #   如果能直接到达守卫点，那应该考虑一下直接到达 ... 而不要先把基地的墙凿了
            #
            if battler.is_closest_to(base):
                player.set_status(Status.GRARD_OUR_BASE)

                moreDangerousPoint = None
                _shouldMoveToDangerousPoint = False
                #
                # 已到达基地附近，但是未到达守卫点，尝试移向守卫点
                #
                if (battler.xy not in self._GUARD_POINTS  # 为处在对角线防御位置
                    and not player.has_status(Status.BLOCK_ROAD_FOR_OUR_BASE) # 高优先级触发
                    ):
                    moreDangerousPoint = self._get_more_dangerous_guard_point(oppBattler)
                    _shouldMoveToDangerousPoint = True


                #
                # 已经到达守卫点，判断是否需要移向另一个守卫点
                #
                if battler.xy in self._GUARD_POINTS:
                    distancesToEnemy = [ oppBattler.get_manhattan_distance_to_point(x2, y2)
                                            for (x2, y2) in self._GUARD_POINTS ]
                    moreDangerousPoint = self._GUARD_POINTS[ np.argmin(distancesToEnemy) ] # 距离敌人更近的点根据危险性
                    _shouldMoveToDangerousPoint = True

                if _shouldMoveToDangerousPoint:
                    action = self._get_next_action_to_guard_point(*moreDangerousPoint, oppBattler)
                    if not Action.is_stay(action):
                        player.set_status(Status.MOVE_TO_ANOTHER_GUARD_POINT)
                    else:
                        player.set_status(Status.STAY_FOR_GUARDING_OUR_BASE)
                    return action

                player.set_status(Status.STAY_FOR_GUARDING_OUR_BASE) # 设置为等待
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

                    if Action.is_stay(action) and battler.is_closest_to(base): # 到达基地就等待了
                        returnAction = action
                        raise OUTER_BREAK

                    realAction = self._try_make_decision(action, oppBattler)

                    if Action.is_stay(realAction): # 尽量找一条不是停留的路？
                        player.remove_status(Status.FORCED_WITHDRAW)
                        continue

                    returnAction = realAction
                    raise OUTER_BREAK

            if not Action.is_valid(returnAction): # 没有一个合适的行为？
                action = battler.get_next_defensive_action(_route1) # 那就随便来一个把 ...
                returnAction = self._try_make_decision(action, oppBattler)

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
