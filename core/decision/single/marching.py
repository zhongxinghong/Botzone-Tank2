# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 16:16:03
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-20 11:39:48

__all__ = [

    "MarchingDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...utils import outer_label, debug_print, debug_pprint
from ...action import Action
from ...field import BrickField
from ...tank import BattleTank
from ...strategy.status import Status
from ...strategy.signal import Signal
from ...strategy.evaluate import estimate_enemy_effect_on_route

#{ BEGIN }#

class MarchingDecision(SingleDecisionMaker):
    """
    行军策略
    -------------------------

    当身边没有和任何敌人正面遭遇的时候，尝试寻找最佳的进攻行为

    1. 进攻
    2. 不会主动破墙
    3. 遇到僵局，会在指定回合后自动打破僵局
    4. 遇到有风险的路径导致需要停止不前的，会考虑寻找相同长度但是安全的路径，并改变方向


    团队信号：
    ----------
    1. 破墙信号
    2. 强攻信号

    """
    def _make_decision(self):

        player      = self._player
        Tank2Player = type(player)

        signal  = self._signal
        map_    = player._map
        tank    = player.tank
        battler = player.battler


        # (inserted) 强攻信号
        #-------------------------
        if signal == Signal.FORCED_MARCH:
            attackAction = battler.get_next_attack_action() # 应该是移动行为，且不需检查安全性
            player.set_status(Status.READY_TO_FORCED_MARCH)
            return ( attackAction, Signal.READY_TO_FORCED_MARCH )


        oppTank = battler.get_nearest_enemy()
        oppBattler = BattleTank(oppTank)

        myRoute = battler.get_shortest_attacking_route()
        oppRoute = oppBattler.get_shortest_attacking_route()
        # assert not myRoute.is_not_found() and not oppRoute.is_not_found(), "route not found" # 一定能找到路
        if myRoute.is_not_found() or oppRoute.is_not_found():
            # 可能出现这种队友堵住去路的及其特殊的情况！ 5cdde41fd2337e01c79f1284
            allowedDelay = 0
        else:
            leadingLength = oppRoute.length - myRoute.length

            if leadingLength <= 0:
                allowedDelay = 0 # 不必别人领先的情况下，就不要 delay 了 ...
            else:
                allowedDelay = leadingLength # 允许和对手同时到达，但由于我方先手，实际上应该是领先的

        #
        # 在我方地盘时，优先从边路攻击
        # 到达敌方场地，优先从中路攻击
        #
        # 5cde18e7d2337e01c79f47c8
        #
        isMiddleFirst = battler.is_in_enemy_site()


        returnAction = Action.STAY # 将会返回的行为，默认为 STAY
        with outer_label() as OUTER_BREAK:
            #
            # TODO:
            #   仅仅在此处综合考虑路线长度和敌人的影响，有必要统一让所有尝试获得下一步行为的函数都
            #   以于此处相同的方式获得下一攻击行为
            #
            # for route in battler.get_all_shortest_attacking_routes(): # 目的是找到一个不是停留的动作，避免浪费时间
            # for route in sorted_routes_by_enemy_effect(
            #                 battler.get_all_shortest_attacking_routes(delay=allowedDelay), player ):
            for route in sorted( battler.get_all_shortest_attacking_routes(delay=allowedDelay, middle_first=isMiddleFirst),
                                    key=lambda r: estimate_enemy_effect_on_route(r, player) ):

                # 首先清除可能出现的状态，也就是导致 stay 的状况
                player.remove_status( Status.WAIT_FOR_MARCHING,
                                    Status.PREVENT_BEING_KILLED,
                                    Status.HAS_ENEMY_BEHIND_BRICK )

                attackAction = battler.get_next_attack_action(route)

                if Action.is_stay(attackAction): # 下一步是停留，就没必要过多判断了
                    returnAction = attackAction
                    raise OUTER_BREAK

                realAction = player.try_make_decision(attackAction)
                if Action.is_stay(realAction): # 存在风险
                    if Action.is_move(attackAction):

                        # 特殊情况，如果下下回合就要打掉对方基地
                        # 那就没必要乱跑了 5cddde4dd2337e01c79f0ba3
                        #
                        if battler.is_face_to_enemy_base():
                            returnAction = realAction
                            raise OUTER_BREAK

                        # (inserted) 主动打破僵局：因为遇到敌人，为了防止被射杀而停留
                        # 注：
                        #   在上方的主动防御模式里还有一段和这里逻辑基本一致的代码
                        #--------------------------
                        if (player.has_status_in_previous_turns(Status.WAIT_FOR_MARCHING, turns=1)
                            and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1)
                            ): # 即将停留第二回合
                            oppBattler = BattleTank(player.get_risk_enemy())
                            oppPlayer = Tank2Player(oppBattler)
                            #
                            # 判断敌人不会攻击我的标准
                            #
                            # 1. 敌人当前回合可以射击
                            # 2。 敌人上回合也可以射击
                            # 3. 敌人上回合与上上回合的行为相同，也就是已经连续移动了两个回合或者等待了两个回合
                            #    这个补充条件非常重要 5cde71a4d2337e01c79f9a77
                            #
                            #    TODO:
                            #       这个条件仍然不对！！ 5ce220add2337e01c7a38462
                            #
                            if (oppBattler.canShoot # 当回合可以射击
                                and not oppPlayer.has_status_in_previous_turns(Status.RELOADING) # 上回合也可以射击
                                and oppPlayer.get_previous_action(back=1) == oppPlayer.get_previous_action(back=2)
                                ): # 说明敌人大概率不打算攻击我
                                if (Action.is_move(oppPlayer.get_previous_action(back=1))
                                    and battler.get_manhattan_distance_to(oppBattler) == 2
                                    ): # 这种情况对应着对方刚刚到达拐角处，这种情况是有危险性的，因此再停留一回合 5cd4045c86d50d05a00840e1
                                    pass
                                else:
                                    # TODO:
                                    #   此处需要检查是否应该预先破墙 5ce21ba2d2337e01c7a37dbd
                                    #
                                    player.set_status(Status.KEEP_ON_MARCHING)
                                    returnAction = attackAction
                                    raise OUTER_BREAK

                        # 原本的移动，现在变为停留
                        #------------------------
                        # 停着就是在浪费时间，不如选择进攻
                        #
                        fields = battler.get_destroyed_fields_if_shoot(attackAction)

                        #
                        # 如果当前回合射击可以摧毁的对象中，包含自己最短路线上的块
                        # 那么就射击
                        #
                        for field in fields:
                            if route.has_block(field): # 为 block 对象，该回合可以射击
                                action = player.try_make_decision(battler.shoot_to(field))
                                if Action.is_shoot(action):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    player.set_status(Status.WAIT_FOR_MARCHING)
                                    player.set_status(Status.PREVENT_BEING_KILLED)
                                    returnAction = action
                                    raise OUTER_BREAK
                        #
                        # 如果能摧毁的是基地外墙，仍然选择攻击
                        # 因为在攻击后可能可以给出更加短的路线
                        #
                        for field in fields:
                            if battler.check_is_outer_wall_of_enemy_base(field):
                                action = player.try_make_decision(battler.shoot_to(field))
                                if Action.is_shoot(action):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    player.set_status(Status.WAIT_FOR_MARCHING)
                                    player.set_status(Status.PREVENT_BEING_KILLED)
                                    returnAction = action
                                    raise OUTER_BREAK

                        #
                        # 如果不能摧毁和地方基地周围的墙，但是可以摧毁与自己中间相差一格的墙，那么仍然选择攻击
                        # 这种情况多半属于，如果当前回合往前走一步，可能被垂直方向的敌人射杀，因为不敢前进
                        # 在多回合后，我方可能会主动突破这种僵持情况。在我方主动向前一步的时候，敌人将可以
                        # 射击我方坦克。如果前方有一个空位，那么我方坦克就可以闪避到前方的空位上，从而继续前进。
                        # 如果这个位置本来是个砖块，但是没有预先摧毁，我方坦克在突击后就只能选择原路闪回，
                        # 那么就可能出现僵局
                        # 因此这里预先摧毁和自己相差一格的土墙，方便后续突击
                        #
                        # 如果是防御状态，那么不要随便打破墙壁！ 5cd31d84a51e681f0e91ca2c
                        #
                        if (not player.has_status(Status.DEFENSIVE)  # 防御性无效
                            and battler.is_in_enemy_site()  # 只有在对方基地的时候才有效
                            ):
                            for field in fields:
                                if (isinstance(field, BrickField)
                                    and battler.get_manhattan_distance_to(field) == 2 # 距离为 2 相当于土墙
                                    and battler.canShoot
                                    ):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    player.set_status(Status.WAIT_FOR_MARCHING)
                                    player.set_status(Status.PREVENT_BEING_KILLED)
                                    player.set_status(Status.READY_TO_CLEAR_A_ROAD_FIRST)
                                    returnAction = battler.shoot_to(field)
                                    raise OUTER_BREAK


                    elif Action.is_shoot(attackAction):
                        # 如果为射击行为，检查是否是墙后敌人造成的
                        enemy = battler.get_enemy_behind_brick(attackAction)
                        if enemy is not None:
                            player.set_risk_enemy(BattleTank(enemy)) # 额外指定一下，确保是这个敌人造成的
                            player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)


                    # 否则停止不前
                    # 此时必定有 riskyEnemy
                    #
                    player.set_status(Status.WAIT_FOR_MARCHING) # 可能触发 Signal.PREPARE_FOR_BREAK_BRICK 和 Signal.FORCED_MARCH
                    player.set_status(Status.PREVENT_BEING_KILLED) # TODO: 这个状态是普适性的，希望在上面的各种情况中都能补全
                    returnAction = Action.STAY
                    continue # 停留动作，尝试继续寻找

                # 对于移动行为，有可能处于闪避到远路又回来的僵局中 5cd009e0a51e681f0e8f3ffb
                # 因此在这里根据前期状态尝试打破僵局
                #----------------------------------
                if (player.has_status_in_previous_turns(Status.WILL_DODGE_TO_LONG_WAY, turns=1) # 说明上回合刚闪避回来
                    and Action.is_move(realAction) # 然后这回合又准备回去
                    ):
                    # TODO:
                    #   此处是否有必要进一步检查两次遇到的敌人为同一人？
                    #
                    #
                    # 首先考虑前方相距一格处是否有土墙，如果有，那么就凿墙 5cd009e0a51e681f0e8f3ffb
                    #
                    fields = battler.get_destroyed_fields_if_shoot(realAction)
                    for field in fields:
                        if isinstance(field, BrickField):
                            if (battler.get_manhattan_distance_to(field) == 2
                                and battler.canShoot
                                ):
                                player.set_status(Status.KEEP_ON_MARCHING) # 真实体现
                                returnAction = battler.shoot_to(field)
                                raise OUTER_BREAK
                    # TODO:
                    #   还可以选择绕路？



                # 预判一步，如果下一步会遇到敌人，并且不得不回头闪避的话，就考虑先摧毁与自己中间相差一格的墙（如果存在）
                # 类似于主动防御的情况
                #
                if Action.is_move(realAction):
                    if (not player.has_status(Status.DEFENSIVE) #　防御性无效
                        and battler.is_in_enemy_site()  # 只有在敌方地盘时才有效！
                        ):
                        _needToBreakWallFirst = True
                        with map_.simulate_one_action(battler, realAction):
                            enemies = battler.get_enemies_around()
                            if len(enemies) == 0: # 没有敌人根本不需要预判
                                _needToBreakWallFirst = False
                            else:
                                with outer_label() as OUTER_BREAK:
                                    route1 = battler.get_shortest_attacking_route()
                                    for enemy in battler.get_enemies_around():
                                        for action in battler.try_dodge(enemy):
                                            with map_.simulate_one_action(battler, action):
                                                route2 = battler.get_shortest_attacking_route() # 只有 route1 为 delay = 0 的选择才可比较
                                                if route2.length <= route1.length:  # 如果存在着一种闪避方法使得闪避后线路长度可以不超过原线路长度
                                                    _needToBreakWallFirst = False  # 那么就不破墙
                                                    raise OUTER_BREAK

                        if _needToBreakWallFirst: # 现在尝试破墙
                            shootAction = realAction + 4
                            for field in battler.get_destroyed_fields_if_shoot(shootAction):
                                if isinstance(field, BrickField):
                                    if battler.get_manhattan_distance_to(field) == 2: # 距离为 2 的土墙
                                        if battler.canShoot:
                                            player.set_status(Status.WAIT_FOR_MARCHING)
                                            player.set_status(Status.READY_TO_CLEAR_A_ROAD_FIRST)
                                            returnAction = shootAction # 不检查安全性
                                            raise OUTER_BREAK

                        if _needToBreakWallFirst: # 需要射击但是前面没有射击，那么就等待
                            player.set_status(Status.WAIT_FOR_MARCHING)
                            returnAction = Action.STAY
                            continue


                #
                # move action 在这之前必须要全部处理完！
                #
                #
                #
                # 侵略模式下优先射击，如果能够打掉处在最短路线上的墙壁
                #-------------------
                if (player.has_status(Status.AGGRESSIVE)
                    and Action.is_move(realAction)
                    and battler.canShoot
                    ):
                    shootAction = realAction + 4
                    for field in battler.get_destroyed_fields_if_shoot(shootAction):
                        if isinstance(field, BrickField) and field.xy in route: # 能够打掉一个处于最短路线上的土墙
                            action = player.try_make_decision(shootAction)
                            if Action.is_shoot(action):
                                player.set_status(Status.KEEP_ON_MARCHING)
                                realAction = shootAction # 注意：这里修改了 realAction 方便后续判断，但是这是非常不好的一个做法
                                break

                #
                # 禁止随便破墙！容易导致自己陷入被动！
                #
                if Action.is_shoot(realAction):
                    #
                    # 敌人处在墙后的水平路线上，并且与墙的间隔不超过 1 个空格 5cd33a06a51e681f0e91de95
                    # 事实上 1 个空格是不够的！ 5cd35e08a51e681f0e92182e
                    #
                    _shouldStay = False
                    oppBattler  = None

                    enemy = battler.get_enemy_behind_brick(realAction, interval=-1)
                    if enemy is not None: # 墙后有人，不能射击
                        # 否则就等待
                        #---------------
                        player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)
                        player.set_status(Status.WAIT_FOR_MARCHING)
                        _shouldStay = True
                    #
                    # 敌人下一步可能移到墙后面
                    #
                    if not _shouldStay:
                        with outer_label() as OUTER_BREAK:
                            for oppBattler in [ _oppPlayer.battler for _oppPlayer in player.opponents ]:
                                if oppBattler.destroyed:
                                    continue
                                x1, y1 = oppBattler.xy
                                for x2, y2 in oppBattler.get_surrounding_empty_field_points():
                                    moveAction = Action.get_move_action(x1, y1, x2, y2)
                                    assert map_.is_valid_move_action(oppBattler, moveAction)
                                    with map_.simulate_one_action(oppBattler, moveAction):
                                        if battler.get_enemy_behind_brick(realAction, interval=-1) is not None: # 此时如果直接出现在墙的后面
                                            player.set_status(Status.WAIT_FOR_MARCHING)
                                            _shouldStay = True
                                            raise OUTER_BREAK

                    #
                    # 并不是一定不能破墙，需要检查敌人是否真的有威胁 5ce209c1d2337e01c7a36a0a
                    #
                    # 此处应该交给强攻信号处理？
                    #
                    if _shouldStay and oppBattler is not None:
                        teammateBattler = player.teammate.battler
                        for enemy in teammateBattler.get_enemies_around():
                            if enemy is oppBattler.tank: # 被队友牵制的敌人可以忽略
                                _shouldStay = False
                                break


                    if _shouldStay:
                        # 先尝试 shoot 转 move
                        #---------------
                        if Action.is_shoot(realAction):
                            moveAction = realAction - 4
                            action = player.try_make_decision(moveAction)
                            if Action.is_move(action):
                                returnAction = action
                                break

                    if _shouldStay: # 否则 stay
                        returnAction = Action.STAY
                        continue


                # 否则继续攻击
                player.set_status(Status.KEEP_ON_MARCHING)
                returnAction = realAction
                raise OUTER_BREAK

            # endfor
        # endwith

        # 找到一个侵略性的行为
        if not Action.is_stay(returnAction):
            return returnAction

        # 否则返回 STAY
        player.set_status(Status.WAIT_FOR_MARCHING)
        return Action.STAY


#{ END }#