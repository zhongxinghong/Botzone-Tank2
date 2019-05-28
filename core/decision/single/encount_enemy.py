# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 18:05:23
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 04:07:25

__all__ = [

    "EncountEnemyDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...utils import outer_label, debug_print
from ...action import Action
from ...field import BrickField
from ...strategy.status import Status
from ...strategy.label import Label
from ...strategy.evaluate import evaluate_aggressive
from .withdrawal import WithdrawalDecision
from .base_defense import BaseDefenseDecision

#{ BEGIN }#

class EncountEnemyDecision(SingleDecisionMaker):
    """
    遭遇敌人时的决策

    """
    def _make_decision(self):

        player   = self._player
        signal   = self._signal
        map_     = player._map
        tank     = player.tank
        battler  = player.battler
        teammate = player.teammate

        Tank2Player = type(player)
        BattleTank  = type(battler)

        aroundEnemies = battler.get_enemies_around()
        if len(aroundEnemies) > 0:
            player.set_status(Status.ENCOUNT_ENEMY)

            if len(aroundEnemies) > 1: # 两个敌人，尝试逃跑
                assert len(aroundEnemies) == 2 # 可能会遇到极其罕见的三人重叠

                # 首先判断是否为真正的双人夹击
                enemy1, enemy2 = aroundEnemies
                x, y = tank.xy
                x1, y1 = enemy1.xy
                x2, y2 = enemy2.xy

                # 先判断敌人是否重叠，如果是，那么很有可能直接击杀！
                if (x1, y1) == (x2, y2):
                    if (not teammate.defeated # 队友还没有死，自己可以考虑牺牲
                        and battler.canShoot
                        ):
                        player.set_status(Status.ENCOUNT_TWO_ENEMY)
                        player.set_status(Status.READY_TO_DOUBLE_KILL_ENEMIES)
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        return battler.shoot_to(enemy1)

                if x1 == x2 == x:
                    if (y > y1 and y > y2) or (y < y1 and y < y2):
                        player.set_status(Status.ENCOUNT_ONE_ENEMY)
                        pass # 实际可视为一个人
                elif y1 == y2 == y:
                    if (x > x1 and x > x2) or (x < x1 and x < x2):
                        player.set_status(Status.ENCOUNT_ONE_ENEMY)
                        pass
                else: # 真正的被夹击
                    player.set_status(Status.ENCOUNT_TWO_ENEMY)
                    oppBattlers = [ BattleTank(_enemy) for _enemy  in aroundEnemies ]
                    if all( oppBattler.canShoot for oppBattler in oppBattlers ):
                        # 如果两者都有弹药，可能要凉了 ...
                        player.set_status(Status.DYING)
                        if battler.canShoot:
                            # TODO: 这种情况下有选择吗？
                            player.set_status(Status.READY_TO_FIGHT_BACK)
                            return battler.shoot_to(enemy1) # 随便打一个？
                    elif all( not oppBattler.canShoot for oppBattler in oppBattlers ):
                        # 均不能进攻的话，优先闪避到下回合没有敌人的位置（优先考虑拆家方向）
                        firstMoveAction = tuple()
                        attackAction = battler.get_next_attacking_action()
                        if Action.is_move(attackAction): # 如果是移动行为
                            firstMoveAction = ( attackAction, )
                        for action in firstMoveAction + Action.MOVE_ACTIONS:
                            if map_.is_valid_move_action(tank, action):
                                with map_.simulate_one_action(tank, action):
                                    if len( battler.get_enemies_around() ) < 2: # 一个可行的闪避方向
                                        player.set_status(Status.READY_TO_DODGE)
                                        return action
                        # 均不能闪避，应该是处在狭道内，则尝试任意攻击一个
                        if battler.canShoot:
                            # TODO: 是否有选择？
                            player.set_status(Status.READY_TO_FIGHT_BACK)
                            return battler.shoot_to(enemy1) # 随便打一个
                    else: # 有一个能射击，则反击他
                        for oppBattler in oppBattlers:
                            if oppBattler.canShoot: # 找到能射击的敌人
                                actions = battler.try_dodge(oppBattler)
                                if len(actions) == 0: # 不能闪避
                                    if battler.canShoot:
                                        player.set_status(Status.READY_TO_FIGHT_BACK)
                                        return battler.shoot_to(oppBattler)
                                    else: # 要凉了 ...
                                        break
                                elif len(actions) == 1:
                                    action = player.try_make_decision(actions[0])
                                else:
                                    action = player.try_make_decision(actions[0],
                                                player.try_make_decision(actions[1]))
                                if Action.is_move(action): # 统一判断
                                    player.set_status(Status.READY_TO_DODGE)
                                    return action
                                # 没有办法？尝试反击
                                if battler.canShoot:
                                    player.set_status(Status.READY_TO_FIGHT_BACK)
                                    return battler.shoot_to(oppBattler)
                                else: # 要凉了
                                    break
                        # 没有办法对付 ..
                        player.set_status(Status.DYING)
                    # 无所谓的办法了...
                    return player.try_make_decision(battler.get_next_attacking_action())

            # TODO:
            #   虽然说遇到了两个一条线上的敌人，但是这不意味着后一个敌人就没有威胁 5ccee460a51e681f0e8e5b17


            # 当前情况：
            # ---------
            # 1. 敌人数量为 2 但是一个处在另一个身后，或者重叠，可视为一架
            # 2. 敌人数量为 1
            #
            if len(aroundEnemies) == 1:
                oppTank = aroundEnemies[0]
            else: # len(aroundEnemies) == 2:
                oppTank = battler.get_nearest_enemy()
            oppBattler = BattleTank(oppTank)
            oppPlayer = Tank2Player(oppBattler)

            #
            # (inserted) 判断上回合敌人是否和我重叠，用于标记敌人 5ce52a48d2337e01c7a714c7
            #
            if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                and not player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=2)
                and not Action.is_move(player.get_previous_action(back=1)) # 且不是因为我方主动打破重叠导致
                ): # 上回合刚刚进入重叠，这回合就被打破
                with map_.rollback_to_previous():
                    if oppTank is battler.get_overlapping_enemy():
                        oppPlayer.add_labels(Label.IMMEDIATELY_BREAK_OVERLAP_BY_MOVE)


            #
            # 在非 WITHDRAW 的情况下，评估当前侵略性
            #
            if not player.has_status(Status.WITHDRAW):
                _allowWithdraw = ( WithdrawalDecision.ALLOW_WITHDRAWAL
                                    and not player.has_label(Label.DONT_WITHDRAW) )
                status = evaluate_aggressive(battler, oppBattler, allow_withdraw=_allowWithdraw)
                player.set_status(status)
            else:
                status = Status.WITHDRAW

            # 侵略模式/僵持模式
            #----------
            # 1. 优先拆家
            # 2. 只在必要的时刻还击
            # 3. 闪避距离不宜远离拆家路线
            #
            if status == Status.AGGRESSIVE or status == Status.STALEMENT:
                if not oppBattler.canShoot:
                    # 如果能直接打死，那当然是不能放弃的！！
                    if len( oppBattler.try_dodge(battler) ) == 0: # 必死
                        if battler.canShoot:
                            player.set_status(Status.READY_TO_KILL_ENEMY)
                            return battler.shoot_to(oppBattler)

                    attackAction = battler.get_next_attacking_action() # 其他情况，优先进攻，不与其纠缠
                    realAction = player.try_make_decision(attackAction) # 默认的进攻路线
                    if Action.is_stay(realAction): # 存在风险
                        if Action.is_move(attackAction):
                            #
                            # 原本移动或射击，因为安全风险而变成停留，这种情况可以尝试射击，充分利用回合数
                            #
                            # TODO:
                            #   实际上，很多时候最佳路线选择从中线进攻，但从两侧进攻也是等距离的，
                            #   在这种情况下，由于采用从中线的进攻路线，基地两侧的块并不落在线路上，因此会被
                            #   忽略，本回合会被浪费。但是进攻基地两侧的块往往可以减短路线。因此此处值得进行
                            #   特殊判断
                            #
                            fields = battler.get_destroyed_fields_if_shoot(attackAction)
                            route = battler.get_shortest_attacking_route()
                            for field in fields:
                                if route.has_block(field): # 为 block 对象，该回合可以射击
                                    action = player.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        player.set_status(Status.PREVENT_BEING_KILLED)
                                        player.set_status(Status.KEEP_ON_MARCHING)
                                        return action
                            # TODO: 此时开始判断是否为基地外墙，如果是，则射击
                            for field in fields:
                                if battler.check_is_outer_wall_of_enemy_base(field):
                                    action = player.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        player.set_status(Status.PREVENT_BEING_KILLED)
                                        player.set_status(Status.KEEP_ON_MARCHING)
                                        return action


                        # 刚刚对射为两回合，该回合双方都没有炮弹，尝试打破僵局
                        #---------------------------------------------------
                        # 当前为侵略性的，并且在对方地盘，尝试回退一步，与对方重叠。
                        #   后退操作必须要有限制 5cd10315a51e681f0e900fa8
                        #
                        # 如果一直回头，尝试在这一步选择非回头的其他行为 5ced8eee641dd10fdcc7907f
                        #
                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=3)
                            and Action.is_stay(player.get_previous_action(back=2))    # 还需要检查两者上上回合是否为等待
                            and Action.is_stay(oppPlayer.get_previous_action(back=2)) # 避免将边移动边对射的情况考虑进来
                            and battler.is_in_enemy_site()         # 添加必须在对方地盘的限制，避免在我方地盘放人
                            and player.has_status(Status.AGGRESSIVE) # 只有侵略性的状态可以打破僵局
                            ):
                            # 判断是否为反复回头
                            if player.has_status_recently(Status.READY_TO_BACK_AWAY, turns=6): # 最近几回合内是否曾经回头过
                                player.add_labels(Label.ALWAYS_BACK_AWAY)

                            if (player.has_label(Label.ALWAYS_BACK_AWAY)
                                and not battler.is_in_our_site(include_midline=True) # 严格不在我方基地
                                ): # 考虑用闪避的方式代替后退
                                for action in battler.try_dodge(oppBattler):
                                    realAction = player.try_make_decision(action)
                                    if Action.is_move(realAction):
                                        player.set_status(Status.TRY_TO_BREAK_ALWAYS_BACK_AWAY)
                                        player.remove_labels(Label.ALWAYS_BACK_AWAY) # 删掉这个状态
                                        return realAction

                            # 否则继续回头
                            backMoveAction = battler.back_away_from(oppBattler)
                            action = player.try_make_decision(backMoveAction)
                            if Action.is_move(action):
                                player.set_status(Status.READY_TO_BACK_AWAY)
                                return action


                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=1) # 上回合正在和对方对射
                            and not battler.canShoot    # 但是我方本回合不能射击
                            and not oppBattler.canShoot # 并且对方本回合不能射击
                            ):
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射状态，用于后方打破僵持

                        # 其余情况照常
                        player.set_status(Status.PREVENT_BEING_KILLED)
                        return realAction
                    # 否则不予理会，直接移动或者反击
                    action = player.try_make_decision(battler.get_next_attacking_action())
                    if not Action.is_stay(action):
                        # 补丁
                        #----------------------------
                        # 针对两者距离为 2 的情况，不能一概而论！
                        #
                        if status == Status.STALEMENT: # 僵持模式考虑堵路
                            _route = battler.get_route_to_enemy_by_move(oppBattler)
                            if _route.is_not_found():
                                _route = battler.get_route_to_enemy_by_move(oppBattler, block_teammate=False)
                            assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                            assert _route.length > 0, "unexpected overlapping enemy"
                            if _route.length == 2:
                                if not player.is_suitable_to_overlap_with_enemy(oppBattler): # 更适合堵路
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                        # 其他情况均可以正常移动
                        #player.set_status(Status.KEEP_ON_MARCHING)
                        #return action
                        return # 直接抛出让后面的 decision 处理，当做没有这个敌人

                    #  不能移动，只好反击
                    action = player.try_make_decision(battler.shoot_to(oppBattler))
                    if Action.is_shoot(action):
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        return action
                else:
                    # 对方有炮弹，需要分情况 5ccb3ce1a51e681f0e8b4de1
                    #-----------------------------
                    # 1. 如果是侵略性的，则优先闪避，并且要尽量往和进攻路线方向一致的方向闪避，否则反击
                    # 2. 如果是僵持的，那么优先堵路，类似于 Defensive
                    #
                    # TODO:
                    #   可能需要团队信号协调 5ccc30f7a51e681f0e8c1668
                    #
                    if status == Status.STALEMENT:
                        #
                        # 首先把堵路的思路先做了，如果不能射击，那么同 aggressive
                        #
                        # TODO:
                        #   有的时候这并不是堵路，而是在拖时间！ 5ccf84eca51e681f0e8ede59

                        # 上一回合保持重叠，但是却被敌人先过了，这种时候不宜僵持，应该直接走人
                        # 这种情况下直接转为侵略模式！
                        #
                        if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                            and (player.has_status_in_previous_turns(Status.READY_TO_BLOCK_ROAD, turns=1)
                                or player.has_status_in_previous_turns(Status.KEEP_ON_OVERLAPPING, turns=1))
                            ):
                            pass # 直接过到侵略模式
                        else:
                            # 否则算作正常的防守
                            #
                            # TODO:
                            #   射击不一定正确，因为敌人可能上回合刚把我过掉，此时应该考虑主动闪走！
                            #   5ce4e66cd2337e01c7a6abd7
                            #
                            if battler.canShoot:

                                #
                                # (inserted) 先看上回合是不是刚被对方过掉
                                #
                                _justBreakOverlap = False
                                with map_.rollback_to_previous():
                                    if (battler.has_overlapping_enemy()
                                        and oppTank is battler.get_overlapping_enemy()
                                        ): # 刚刚被对手打破重叠
                                        _justBreakOverlap = True

                                _shouldShoot = False
                                if _justBreakOverlap: # 刚刚被对手主动打破重叠
                                    for _route in battler.get_all_shortest_attacking_routes():
                                        if oppTank.xy in _route:  # 对方现在位于我的攻击路线上，说明对方上回合是
                                            _shouldShoot = True   # 回头堵路，那么继续保持射击
                                            break

                                if _shouldShoot: # 正常防御
                                    player.set_status(Status.READY_TO_BLOCK_ROAD, Status.READY_TO_FIGHT_BACK)
                                    if battler.on_the_same_line_with(oppBattler, ignore_brick=False):
                                        player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射
                                    return battler.shoot_to(oppBattler)
                                else:
                                    pass # 否则视为进攻逻辑

                    # 闪避，尝试找最佳方案
                    #-------------------------
                    defenseAction = Action.STAY
                    if battler.canShoot:
                        defenseAction = battler.shoot_to(oppBattler)


                    dodgeActions = battler.try_dodge(oppTank)

                    if battler.is_in_enemy_site(): # 限制条件，只有在对方基地才开始闪现！

                        #
                        # 最佳方向是闪避向着进攻方向移动
                        #
                        attackAction = battler.get_next_attacking_action()
                        for action in dodgeActions: # 与进攻方向相同的方向是最好的
                            if Action.is_same_direction(action, attackAction):
                                realAction = player.try_make_decision(action) # 风险评估
                                if Action.is_move(realAction):
                                    player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                    return realAction # 闪避加行军


                        # 没有最佳的闪避方案，仍然尝试闪避
                        #-----------------------------
                        # 但是不能向着增加攻击线路长短的方向闪避！
                        #
                        route1 = battler.get_shortest_attacking_route()
                        for action in dodgeActions:
                            realAction = player.try_make_decision(action)
                            if Action.is_move(realAction):
                                with map_.simulate_one_action(battler, action):
                                    route2 = battler.get_shortest_attacking_route()
                                if route2.length > route1.length: # 不能超过当前路线长度，否则就是浪费一回合
                                    continue
                                else:
                                    player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                    return realAction

                        #
                        # 此时还可以考虑借力
                        # 假设下回合两方对射，如果我方尝试闪避，对方会恰好打掉我方进攻路线上的块，那么就闪避
                        #
                        if (len(dodgeActions) > 0         # 存在可用的闪避行为
                            and battler.is_in_enemy_site() # 限制为只有在对方基地才适用这个逻辑
                            ):
                            _shouldDodge = False
                            action = dodgeActions[0]
                            enemyShootAction = oppBattler.shoot_to(battler)
                            with outer_label() as OUTER_BREAK:
                                with map_.simulate_one_action(battler, action): # 假设闪走
                                    fields = oppBattler.get_destroyed_fields_if_shoot(enemyShootAction)
                                    for field in fields:
                                        if isinstance(field, BrickField): # 对手会打掉墙
                                            for _route in battler.get_all_shortest_attacking_routes():
                                                if field.xy in _route: # 这个块在某一个最短的攻击路线上
                                                    _shouldDodge = True
                                                    raise OUTER_BREAK
                            if _shouldDodge:
                                for action in dodgeActions:
                                    realAction = player.try_make_decision(action)
                                    if Action.is_move(realAction):
                                        player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                        return realAction

                    #
                    # 没有不能不导致路线变长的办法，如果有炮弹，那么优先射击！
                    # 5ccef443a51e681f0e8e64d8
                    #-----------------------------------
                    route1 = battler.get_shortest_attacking_route()
                    if Action.is_shoot(defenseAction):
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        if battler.on_the_same_line_with(oppBattler, ignore_brick=False):

                            # (inserted) 刚刚对射为两回合，该回合尝试闪避敌人，打破僵局
                            #--------------------------------------------
                            # 尝试往远处闪避，创造机会
                            #
                            # 此外，由于敌人这回合必定射击，那么他的炮弹可能会打掉我身后的墙
                            # 这样的可能会创造一些新的机会。有的时候导致该回合必须要与敌人对射的原因，可能是因为
                            # 没有办法开辟攻击路线，而不是敌人堵路。由于闪避的方向是不允许的，也就是另一个更近的
                            # 闪避反向上必定是一个无法摧毁也不能移动到的块，否则会被与先摧毁。
                            # 此时如果可以往背离敌人的方向移动，那么应该不会陷入对射僵局。但事实上是进入了
                            # 这就说明别离敌人的方向是无法移动到的。如果它恰好是一块土墙，那么就可以靠这回合和敌人接力
                            # 来摧毁掉，也许还有往下移动的可能。 5ce429fad2337e01c7a5cd61
                            #
                            if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=4)
                                and Action.is_stay(player.get_previous_action(back=1)) # 检查对应的两个冷却回合是停止
                                and Action.is_stay(player.get_previous_action(back=3)) # 避免将移动对射的情况被考虑进来
                                and Action.is_stay(oppPlayer.get_previous_action(back=1))
                                and Action.is_stay(oppPlayer.get_previous_action(back=3))
                                and battler.is_in_enemy_site()           # 添加必须在对方地盘的限制，避免在我方地盘放人
                                and player.has_status(Status.AGGRESSIVE) # 只有侵略性的状态可以打破僵局
                                ):
                                for action in battler.try_dodge(oppBattler):
                                    if Action.is_move(action):
                                        realAction = player.try_make_decision(action)
                                        if Action.is_move(realAction):
                                            player.set_status(Status.READY_TO_DODGE)
                                            # 这里还是再判断一下距离
                                            route1 = battler.get_shortest_attacking_route()
                                            with map_.simulate_one_action(battler, action):
                                                route2 = battler.get_shortest_attacking_route()
                                                if route2.length > route1.length:
                                                    player.set_status(Status.WILL_DODGE_TO_LONG_WAY)
                                            return realAction

                            # 默认是优先射击
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY)
                            return defenseAction


                    # 如果不能射击，那么终究还是要闪避的
                    # 或者是无法后方移动，为了打破僵局，尝试闪避
                    #----------------------------------
                    for action in dodgeActions:
                        realAction = player.try_make_decision(action)
                        if Action.is_move(realAction):
                            player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                            #
                            # 因为这种情况很有可能会出现死循环 5cd009e0a51e681f0e8f3ffb
                            # 为了后续能够打破这种情况，这里额外添加一个状态进行标记
                            #
                            player.set_status(Status.WILL_DODGE_TO_LONG_WAY)
                            return realAction

                    if Action.is_stay(defenseAction):
                        #
                        # 其实还有一种情况，那就是危险的敌人在自己身上！ 5ceaaacdd2337e01c7adf6a4
                        #
                        riskyEnemyBattler = player.get_risky_enemy()
                        if (riskyEnemyBattler is not None
                            and riskyEnemyBattler is not oppBattler
                            and riskyEnemyBattler.xy == battler.xy
                            ): # 这种情况下实际是没有威胁的 ...
                            for action in dodgeActions:
                                player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                # TODO:
                                #   还需要判断是否向远路闪避 ...
                                #   这里的细节还需要优化，或者这个和自己重叠的条件在前面就要穿插进去
                                return action

                        player.set_status(Status.DYING) # 否则就凉了 ...

                    return defenseAction

                return Action.STAY


            # 防御模式
            #----------
            # 1. 如果对方下回合必死，那么射击
            # 2. 优先堵路，距离远则尝试逼近
            # 3. 必要的时候对抗
            # 4. 距离远仍然优先
            #
            # elif status == DEFENSIVE_STATUS:
                # attackAction = self.try_make_decision(battler.get_next_attacking_action()) # 默认的侵略行为
            elif status == Status.DEFENSIVE:
                if not oppBattler.canShoot:

                    if len( oppBattler.try_dodge(battler) ) == 0:
                        if battler.canShoot: # 必死情况
                            player.set_status(Status.READY_TO_KILL_ENEMY)
                            return battler.shoot_to(oppBattler)
                    #
                    # 不能马上打死，敌人又无法攻击
                    #-------------------------------
                    # 优先堵路，根据双方距离判断
                    #
                    _route = battler.get_route_to_enemy_by_move(oppBattler)
                    if _route.is_not_found():
                        _route = battler.get_route_to_enemy_by_move(oppBattler, block_teammate=False)
                    assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                    assert _route.length > 0, "unexpected overlapping enemy"

                    if _route.length == 1: # 双方相邻，选择等待

                        # 此处首先延续一下对射状态
                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=1) # 上回合正在和对方对射
                            and not battler.canShoot    # 但是我方本回合不能射击
                            and not oppBattler.canShoot # 并且对方本回合不能射击
                            ):
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射状态，用于后方打破僵持

                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY
                    elif _route.length > 2: # 和对方相隔两个格子以上
                        if player.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全逼近
                            action = battler.move_to(oppBattler)
                            player.set_status(Status.READY_TO_BLOCK_ROAD) # 可以认为在堵路 ...
                            return action
                        else:
                            player.set_status(Status.READY_TO_BLOCK_ROAD)
                            return Action.STAY # 否则只好等额爱
                    else: # _route.length == 2:
                        # 相距一个格子，可以前进也可以等待，均有风险
                        #----------------------------------------
                        # 1. 如果对方当前回合无法闪避，下一回合最多只能接近我
                        #    - 如果对方下回合可以闪避，那么我现在等待是意义不大的，不如直接冲上去和他重叠
                        #    - 如果对方下回合仍然不可以闪避，那么我就选择等待，反正它也走不了
                        # 2. 如果对方当前回合可以闪避，那么默认冲上去和他重叠
                        #    - 如果我方可以射击，那么对方应该会判定为闪避，向两旁走，那么我方就是在和他逼近
                        #    - 如果我方不能射击，对方可能会选择继续进攻，如果对方上前和我重叠，就可以拖延时间
                        #
                        # TODO:
                        #    好吧，这里的想法似乎都不是很好 ...
                        #    能不防御就不防御，真理 ...
                        #
                        """if len( oppBattler.try_dodge(battler) ) == 0:
                            # 对手当前回合不可闪避，当然我方现在也不能射击。现在假设他下一步移向我
                            action = oppBattler.move_to(battler) # 对方移向我
                            if map_.is_valid_move_action(oppBattler, action):
                                map_.simulate_one_action(oppBattler, action) # 提交模拟
                                if len( oppBattler.try_dodge(battler) ) == 0:
                                    # 下回合仍然不可以闪避，说明可以堵路
                                    map_.revert()
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                                map_.revert()
                                # 否则直接冲上去
                                if player.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全移动
                                    moveAction = battler.move_to(oppBattler)
                                    player.set_status(Status.READY_TO_BLOCK_ROAD) # 可以认为在堵路
                                    return moveAction
                                else: # 冲上去不安全，那就只能等到了
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                        else:
                            # 对手当前回合可以闪避，那么尝试冲上去和他重叠
                            # TODO:
                            #   可能弄巧成拙 5cca97a4a51e681f0e8ad227
                            #
                            #   这个问题需要再根据情况具体判断！
                            #
                            '''
                            if player.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全重叠
                                moveAction = battler.move_to(oppBattler)
                                player.set_status(Status.READY_TO_BLOCK_ROAD)
                                return moveAction
                            else: # 有风险，考虑等待
                                player.set_status(Status.READY_TO_BLOCK_ROAD)
                                return Action.STAY
                            '''
                            #
                            # TODO:
                            #   是否应该根据战场情况进行判断，比如停下来堵路对方一定无法走通？
                            #
                            #   假设自己为钢墙然后搜索对方路径？
                            #
                            player.set_status(Status.READY_TO_BLOCK_ROAD)
                            return Action.STAY"""
                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY # 似乎没有比这个这个更好的策略 ...
                # 对方可以射击
                else:
                    if battler.canShoot: # 优先反击
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        if battler.on_the_same_line_with(oppBattler, ignore_brick=False):
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 触发对射状态
                        return battler.shoot_to(oppBattler)
                    # 不能反击，只好闪避
                    actions = battler.try_dodge(oppBattler)
                    if len(actions) == 0:
                        player.set_status(Status.DYING) # 凉了 ...
                        action = Action.STAY
                    elif len(actions) == 1:
                        action = player.try_make_decision(actions[0])
                    else: # len(actions) == 2:
                        action = player.try_make_decision(actions[0],
                                        player.try_make_decision(actions[1]))
                    if Action.is_move(action): # 统一判断
                        player.set_status(Status.READY_TO_DODGE)
                        return action
                    # 否则就凉了 ...
                    player.set_status(Status.DYING)

                return Action.STAY

            #
            # 回撤模式
            #------------
            # 1. 优先回撤
            # 2. 如果处在守卫状况，根据所处位置，选择反击或堵路
            #
            elif status == Status.WITHDRAW:
                base = map_.bases[battler.side]
                if not battler.is_closest_to(base):
                    with player.create_snapshot():
                        decision = WithdrawalDecision(player, signal)
                        action = decision.make_decision()
                        if decision.is_handled(action):
                            with map_.simulate_one_action(battler, action):
                                if oppTank not in battler.get_enemies_around(): # 安全行为
                                    return  # 留给 withdraw 处理
                else:
                    # 现在我方坦克已经处在基地附近
                    with player.create_snapshot():
                        decision = BaseDefenseDecision(player, signal)
                        action = decision.make_decision()
                        if decision.is_handled(action): # 符合 base defense 的条件
                            with map_.simulate_one_action(battler, action):
                                if oppTank not in battler.get_enemies_around(): # 安全行为
                                    return  # 留给 base defense
                #
                # 否则就是不安全行为，应该予以反击
                #
                if battler.canShoot:
                    player.set_status(Status.READY_TO_FIGHT_BACK)
                    return battler.shoot_to(oppBattler)
                elif oppBattler.canShoot: # 否则应该闪避
                    for action in battler.try_dodge(oppBattler):
                        player.set_status(Status.READY_TO_DODGE)
                        return action

                if oppBattler.canShoot:
                    player.set_status(Status.DYING) # 不然就凉了 ...

                # 最后就等待
                return Action.STAY


#{ END }#