# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 18:05:23
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-15 18:16:25

__all__ = [

    "EncountEnemyDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...action import Action
from ...tank import BattleTank
from ...strategy.status import Status
from ...strategy.evaluate import evaluate_aggressive

#{ BEGIN }#

class EncountEnemyDecision(SingleDecisionMaker):
    """
    遭遇敌人时的决策

    """
    def _make_decision(self):

        player = self._player

        map_ = player._map
        tank = player.tank
        battler = player.battler

        aroundEnemies = battler.get_enemies_around()
        if len(aroundEnemies) > 0:
            player.set_status(Status.ENCOUNT_ENEMY)
            if len(aroundEnemies) > 1: # 两个敌人，尝试逃跑
                assert len(aroundEnemies) == 2
                # 首先判断是否为真正的双人夹击
                enemy1, enemy2 = aroundEnemies
                x, y = tank.xy
                x1, y1 = enemy1.xy
                x2, y2 = enemy2.xy
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
                        attackAction = battler.get_next_attack_action()
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
                    return player.try_make_decision(battler.get_next_attack_action())

            # TODO:
            #   虽然说遇到了两个一条线上的敌人，但是这不意味着后一个敌人就没有威胁 5ccee460a51e681f0e8e5b17


            # 当前情况：
            # ---------
            # 1. 敌人数量为 2 但是一个处在另一个身后，或者重叠，可视为一架
            # 2. 敌人数量为 1
            if len(aroundEnemies) == 1:
                oppTank = aroundEnemies[0]
            else: # len(aroundEnemies) == 2:
                oppTank = battler.get_nearest_enemy()
            oppBattler = BattleTank(oppTank)

            # 根据当时的情况，评估侵略性
            status = evaluate_aggressive(battler, oppBattler)
            player.set_status(status)

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

                    attackAction = battler.get_next_attack_action() # 其他情况，优先进攻，不与其纠缠
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

                        # 刚刚对射为两回合，尝试打破对射僵局
                        #--------------------------------
                        # 1. 当前为侵略性的，并且在对方地盘，尝试回退一步，与对方重叠。后退操作必须要有限制 5cd10315a51e681f0e900fa8
                        # 2. 可以考虑往远处闪避，创造机会
                        #
                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=3)
                            and battler.is_in_enemy_site()         # 添加必须在对方地盘的限制，避免在我方地盘放人
                            and player.has_status(Status.AGGRESSIVE) # 只有侵略性的状态可以打破僵局
                            ):
                            # 尝试背离敌人
                            #---------------
                            backMoveAction = battler.back_away_from(oppBattler)
                            action = player.try_make_decision(backMoveAction)
                            if Action.is_move(action):
                                player.set_status(Status.READY_TO_BACK_AWAY)
                                return action

                            # 尝试闪避敌人
                            #---------------
                            # 此处需要注意的是，如果能够按近路闪避，那么在射击回合早就闪走了
                            # 所以这里只可能是往远处闪避
                            #
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

                        # 如果之前是对射，在这里需要延续一下对射状态
                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=1) # 上回合正在和对方对射
                            and not battler.canShoot    # 但是我方本回合不能射击
                            and not oppBattler.canShoot # 并且对方本回合不能射击
                            ):
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射状态，用于后方打破僵持

                        # 其余情况照常
                        player.set_status(Status.PREVENT_BEING_KILLED)
                        return realAction
                    # 否则不予理会，直接移动或者反击
                    action = player.try_make_decision(battler.get_next_attack_action())
                    if not Action.is_stay(action):
                        # 补丁
                        #----------------------------
                        # 针对两者距离为 2 的情况，不能一概而论！
                        #
                        if status == Status.STALEMENT: # 僵持模式考虑堵路
                            _route = battler.get_route_to_enemy_by_movement(oppBattler)
                            if _route.is_not_found():
                                _route = battler.get_route_to_enemy_by_movement(oppBattler, block_teammate=False)
                            assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                            assert _route.length > 0, "unexpected overlapping enemy"
                            if _route.length == 2:
                                if not player.is_suitable_to_overlap_with_enemy(oppBattler): # 更适合堵路
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                        # 其他情况均可以正常移动
                        player.set_status(Status.KEEP_ON_MARCHING)
                        return action
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
                        else: # 否则算作正常的防守
                            if battler.canShoot:
                                player.set_status(Status.READY_TO_BLOCK_ROAD, Status.READY_TO_FIGHT_BACK)
                                if battler.get_manhattan_distance_to(oppBattler) == 1:
                                    player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射
                                return battler.shoot_to(oppBattler)

                    # 闪避，尝试找最佳方案
                    #-------------------------
                    defenseAction = Action.STAY
                    if battler.canShoot:
                        defenseAction = battler.shoot_to(oppBattler)
                    actions = battler.try_dodge(oppTank)
                    attackAction = battler.get_next_attack_action()
                    for action in actions: # 与进攻方向相同的方向是最好的
                        if Action.is_move(action) and Action.is_same_direction(action, attackAction):
                            realAction = player.try_make_decision(action) # 风险评估
                            if Action.is_move(realAction):
                                player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                return realAction # 闪避加行军

                    # 没有最佳的闪避方案，仍然尝试闪避
                    #-----------------------------
                    # 但是不能向着增加攻击线路长短的方向闪避！
                    #
                    route1 = battler.get_shortest_attacking_route()
                    for action in actions:
                        if Action.is_move(action):
                            realAction = player.try_make_decision(action)
                            if Action.is_move(realAction):
                                with map_.simulate_one_action(battler, action):
                                    route2 = battler.get_shortest_attacking_route()
                                if route2.length > route1.length: # 不能超过当前路线长度，否则就是浪费一回合
                                    continue
                                else:
                                    player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                    return realAction

                    # 没有不能不导致路线编程的办法，如果有炮弹，那么优先射击！
                    # 5ccef443a51e681f0e8e64d8
                    #-----------------------------------
                    if Action.is_shoot(defenseAction):
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        if battler.get_manhattan_distance_to(oppBattler) == 1:
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY)
                        return defenseAction

                    # 如果不能射击，那么终究还是要闪避的
                    # 或者是无法后方移动，为了打破僵局，尝试闪避
                    #----------------------------------
                    for action in actions:
                        if Action.is_move(action):
                            realAction = player.try_make_decision(action)
                            if Action.is_move(realAction):
                                player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                #
                                # 因为这种情况很有可能会出现死循环 5cd009e0a51e681f0e8f3ffb
                                # 为了后续能够打破这种情况，这里额外添加一个状态进行标记
                                #
                                player.set_status(Status.WILL_DODGE_TO_LONG_WAY)
                                return realAction

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
            else: # status == DEFENSIVE_STATUS or status == STALEMATE_STATUS:
                # attackAction = self.try_make_decision(battler.get_next_attack_action()) # 默认的侵略行为

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
                    _route = battler.get_route_to_enemy_by_movement(oppBattler)
                    if _route.is_not_found():
                        _route = battler.get_route_to_enemy_by_movement(oppBattler, block_teammate=False)
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
                        if battler.get_manhattan_distance_to(oppBattler) == 1:   # 贴脸
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

            # 僵持模式？
            #--------------
            # 双方进攻距离相近，可能持平
            # # TODO:
            #   观察队友？支援？侵略？
            # 1. 优先防御
            # 2. ....
            #
            # elif status == STALEMATE_STATUS:
#{ END }#