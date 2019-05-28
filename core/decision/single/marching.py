# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 16:16:03
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 04:10:11

__all__ = [

    "MarchingDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...utils import outer_label, debug_print, debug_pprint
from ...action import Action
from ...field import BrickField
from ...strategy.status import Status
from ...strategy.signal import Signal
from ...strategy.label import Label
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
    5. ......

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


        # (inserted) 强攻信号
        #-------------------------
        if signal == Signal.FORCED_MARCH:
            attackAction = battler.get_next_attacking_action() # 应该是移动行为，且不需检查安全性
            player.set_status(Status.READY_TO_FORCED_MARCH)
            return ( attackAction, Signal.READY_TO_FORCED_MARCH )


        oppTank = battler.get_nearest_enemy()
        oppBattler = BattleTank(oppTank)
        oppPlayer  = Tank2Player(oppBattler)

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
        isMiddleFirst = False
        # isMiddleFirst = battler.is_in_enemy_site()
        #
        # TODO:
        #   不要采用中路优先的搜索，否则容易打出狭路，然后因为敌人对自己存在威胁而停止不前！
        #   5ce48c2fd2337e01c7a6459b

        isXAxisFirst = False
        #
        # 如果我方两架坦克都到达了敌方基地，处于双方均不回头的局面 5cec9157641dd10fdcc5f30d
        # 那么可以采用 x-axis-first 以更好地触发团队合作，因为它优先选择拆除 x = 4 的墙
        #
        _allPlayers = [ player, teammate, *player.opponents ]
        if (all( _player.battler.is_in_enemy_site(include_midline=True) for _player in _allPlayers )
            and all( not _player.battler.has_enemy_around() for _player in _allPlayers )
            ): # 如果双方都处在对方基地，并且都没有遭遇到敌人
            isMiddleFirst = True # 想要使用 x-axis-first 必须首先 middle-first
            isXAxisFirst = True

        if battler.is_in_our_site():
            #
            # 在我方基地的时候，不要评估敌人对攻击路线的干扰，而是优先采用边路优先的搜索。这样可能和敌人相撞，
            # 但至少可以平局。如果在我方基地就开始衡量敌人的干扰，那么敌人绕边路的时候我方可能会选择中路，
            # 这种情况下可能会被另一边的敌人干扰，出现一牵二的局面。
            #
            # 还可能遇到一种很糟糕的情况，就是我方为了绕开敌人而选择了一条比最短路线要长的路，这种情况下
            # 可能我方最终就会落后与对方，这样如果还绕过了敌人，那就根本没法拦截了，到最后肯定是输。
            #
            # TODO:
            # ----------------------
            # 这个影响对于bot的侵略性影响非常大，因为很容易因此和对方平局。并且边路分拆难以触发合作拆家，
            # 进攻优势会被削弱。也许可以一牵二的情况进行特判，其他情况继续绕路？
            # 也许需要根据情况进行判定，毕竟一牵二的情况和绕路拆家结果反而赢了的情况是有的，而且似乎都不少见
            #
            routes = battler.get_all_shortest_attacking_routes(delay=allowedDelay, middle_first=isMiddleFirst, x_axis_first=isXAxisFirst)
        else:
            routes = sorted( battler.get_all_shortest_attacking_routes(delay=allowedDelay, middle_first=isMiddleFirst, x_axis_first=isXAxisFirst),
                                key=lambda r: estimate_enemy_effect_on_route(r, player) )

        route = None # 这回合的进攻路线
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
            # for route in sorted( battler.get_all_shortest_attacking_routes(delay=allowedDelay, middle_first=isMiddleFirst, x_axis_first=isXAxisFirst),
            #                         key=lambda r: estimate_enemy_effect_on_route(r, player) ):
            for route in routes:
                # 首先清除可能出现的状态，也就是导致 stay 的状况 ？？？？？
                player.remove_status(Status.WAIT_FOR_MARCHING,
                                     Status.PREVENT_BEING_KILLED,
                                     Status.HAS_ENEMY_BEHIND_BRICK)

                attackAction = battler.get_next_attacking_action(route)

                if Action.is_stay(attackAction): # 下一步是停留，就没必要过多判断了
                    returnAction = attackAction
                    raise OUTER_BREAK

                realAction = player.try_make_decision(attackAction)

                # debug_print(player, attackAction, realAction)

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
                            riskyBattler = BattleTank(player.get_risky_enemy())
                            riskyPlayer = Tank2Player(riskyBattler)
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
                            if (riskyBattler.canShoot # 当回合可以射击
                                and not riskyPlayer.has_status_in_previous_turns(Status.RELOADING) # 上回合也可以射击
                                and riskyPlayer.get_previous_action(back=1) == riskyPlayer.get_previous_action(back=2)
                                ): # 说明敌人大概率不打算攻击我
                                if (Action.is_move(riskyPlayer.get_previous_action(back=1))
                                    and battler.get_manhattan_distance_to(riskyBattler) == 2
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
                        enemy = battler.get_enemy_behind_brick(attackAction, interval=-1)
                        if enemy is not None:
                            player.set_risky_enemy(enemy) # 额外指定一下，确保是这个敌人造成的
                            player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)

                        #
                        # 强攻行为，如果出现这种情况，双方均在拆家，但是对方坦克下一步有可能移到我方坦克后方
                        # 对于这种情况，大部分人应该选择继续进攻，同时绕开麻烦，因为进攻的时候还考虑击杀敌人
                        # 一般会延误战机。这种情况下应该判定为敌方坦克不会来尝试击杀我方坦克，那么就继续攻击
                        # 5ce57074d2337e01c7a7b128
                        #
                        oppBattler = player.get_risky_enemy()
                        if (battler.is_in_enemy_site() # 双方均在对方基地方时才触发
                            and oppBattler.is_in_enemy_site()
                            ):
                            #
                            # 现在尝试看对方是否能够找到一条不受到我方坦克影响的最短攻击路线
                            # 通常应该是可以找到的
                            #
                            _consideredActions = set() # 缓存已经考虑过的行为
                            for route in oppBattler.get_all_shortest_attacking_routes():
                                _action = oppBattler.get_next_attacking_action()
                                if _action in _consideredActions:
                                    continue
                                _consideredActions.add(_action)
                                with map_.simulate_one_action(oppBattler, _action):
                                    if not battler.has_enemy_around():
                                        # 说明找到了一条可以躲开我方坦克的路线
                                        player.set_status(Status.KEEP_ON_MARCHING)
                                        returnAction = attackAction
                                        raise OUTER_BREAK


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
                    if battler.will_destroy_a_brick_if_shoot(realAction):
                        field = battler.get_destroyed_fields_if_shoot(realAction)[0]
                        if (not battler.is_in_our_site(field) # 这个 brick 必须不在我方基地！
                            and battler.get_manhattan_distance_to(field) == 2
                            and battler.canShoot
                            ):
                            player.set_status(Status.KEEP_ON_MARCHING) # 真实体现
                            returnAction = battler.shoot_to(field)
                            raise OUTER_BREAK

                    #player.add_label(Label.ALWAYS_DODGE_TO_LONG_WAY) # 如果能够运行到这里，就添加这个标记


                # 预判一步，如果下一步会遇到敌人，并且不得不回头闪避的话，就考虑先摧毁与自己中间相差一格的墙（如果存在）
                # 类似于主动防御的情况
                #
                if Action.is_move(realAction):

                    if battler.is_face_to_enemy_base(ignore_brick=True):
                        # 如果已经和基地处在同一直线上
                        with map_.simulate_one_action(battler, realAction):
                            if not battler.is_face_to_enemy_base(ignore_brick=True):
                                returnAction = Action.STAY # 如果移动后不再面对敌人基地，那么就不移动
                                raise OUTER_BREAK

                    if (not player.has_status(Status.DEFENSIVE) #　防御性无效
                        and battler.is_in_enemy_site()  # 只有在敌方地盘时才有效！
                        and battler.will_destroy_a_brick_if_shoot(realAction) # 如果下回合能射掉一个墙
                        ):
                        _needToBreakWallFirst = True

                        with map_.simulate_one_action(battler, realAction):
                            enemies = battler.get_enemies_around()
                            if len(enemies) == 0: # 没有敌人根本不需要预判
                                _needToBreakWallFirst = False
                            else:
                                with outer_label() as OUTER_BREAK_2:
                                    route1 = battler.get_shortest_attacking_route()
                                    for enemy in battler.get_enemies_around():
                                        for action in battler.try_dodge(enemy):
                                            with map_.simulate_one_action(battler, action):
                                                route2 = battler.get_shortest_attacking_route() # 只有 route1 为 delay = 0 的选择才可比较
                                                if route2.length <= route1.length:  # 如果存在着一种闪避方法使得闪避后线路长度可以不超过原线路长度
                                                    _needToBreakWallFirst = False  # 那么就不破墙
                                                    raise OUTER_BREAK_2

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

                        if (_needToBreakWallFirst
                            and not battler.canShoot # 需要射击但是暂时没有炮弹，那么就等待
                            ):
                            player.set_status(Status.WAIT_FOR_MARCHING)
                            returnAction = Action.STAY
                            continue

                #
                # 考虑这样一种情况，如果下回合我可以射击且对方可以射击，我们中间差两个墙，如果我方不射击
                # 对方可能就会压制过来，这样就很亏，所以当双方都有炮且两者间差一个墙的时候，我方优先射击
                # 5cea974dd2337e01c7add31f
                #
                if (( player.has_status(Status.AGGRESSIVE) or player.has_status(Status.STALEMENT) )
                    and Action.is_move(realAction)
                    and battler.canShoot
                    ):
                    shootAction = realAction + 4
                    _hasEnemyBehindTwoBricks = False
                    oppBattler = None
                    destroyedFields = battler.get_destroyed_fields_if_shoot(shootAction)
                    if (len(destroyedFields) == 1 and isinstance(destroyedFields[0], BrickField) # 前方是墙
                        and battler.get_enemy_behind_brick(shootAction, interval=-1) is None     # 现在墙后无人
                        ):
                        with map_.simulate_one_action(battler, shootAction):
                            destroyedFields = battler.get_destroyed_fields_if_shoot(shootAction)
                            if len(destroyedFields) == 1 and isinstance(destroyedFields[0], BrickField): # 现在前面还有墙
                                enemy = battler.get_enemy_behind_brick(shootAction, interval=-1)
                                if enemy is not None: # 此时墙后有人
                                    _hasEnemyBehindTwoBricks = True
                                    oppBattler = BattleTank(enemy)

                    if _hasEnemyBehindTwoBricks:
                        if oppBattler.canShoot: # 此时对方也可以射击
                            player.set_status(Status.KEEP_ON_MARCHING)
                            returnAction = shootAction # 那么我方这回合优先开炮，避免随后和对方进入僵持阶段
                            raise OUTER_BREAK


                #
                # move action 在这之前必须要全部处理完！
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
                        player.set_risky_enemy(enemy) # 设置这个敌人！
                        player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)
                        player.set_status(Status.WAIT_FOR_MARCHING)
                        _shouldStay = True

                    #
                    # 敌人下一步可能移到墙后面
                    #
                    if not _shouldStay:
                        with outer_label() as OUTER_BREAK_2:
                            for oppBattler in [ _oppPlayer.battler for _oppPlayer in player.opponents ]:
                                if oppBattler.destroyed:
                                    continue
                                for moveAction in oppBattler.get_all_valid_move_actions():
                                    with map_.simulate_one_action(oppBattler, moveAction):
                                        enemy = battler.get_enemy_behind_brick(realAction, interval=-1)
                                        if enemy is not None: # 此时如果直接出现在墙的后面
                                            player.set_status(Status.WAIT_FOR_MARCHING)
                                            player.set_status(Status.ENEMY_MAY_APPEAR_BEHIND_BRICK)
                                            player.set_risky_enemy(enemy) # 仍然将其设置为墙后敌人
                                            _shouldStay = True
                                            raise OUTER_BREAK_2

                    #
                    # 并不是一定不能破墙，需要检查敌人是否真的有威胁
                    #
                    # 1. 和队友相遇的敌人可以忽略 5ce209c1d2337e01c7a36a0a
                    # 2. 和队友隔墙僵持的敌人可以忽略（这种情况非常有可能) 5ce5678ed2337e01c7a79ace
                    # 3. 对手正在和队友僵持的敌人可以忽略 5ce70df6d2337e01c7a98926
                    # 4. 如果对手威胁我的位置他曾经到过，那么可以忽略 5ce266a1d2337e01c7a3cc90
                    #
                    if _shouldStay and oppBattler is not None:
                        teammateBattler = teammate.battler
                        oppTank = oppBattler.tank

                        # 考虑两人相对
                        for enemy in teammateBattler.get_enemies_around():
                            if enemy is oppTank: # 被队友牵制的敌人可以忽略
                                _shouldStay = False
                                break

                        # 考虑是否隔墙僵持
                        _action = teammateBattler.get_next_attacking_action()
                        if not Action.is_stay(_action):
                            enemy = teammateBattler.get_enemy_behind_brick(_action, interval=-1)
                            if enemy is oppTank: # 和队友隔墙僵持的敌人可以忽略
                                _shouldStay = False

                        # 考虑是否和队友僵持
                        if teammateBattler.get_manhattan_distance_to(oppBattler) == 2:
                            _action = oppBattler.get_next_attacking_action()
                            with map_.simulate_one_action(oppBattler, _action): # 模拟一步后和队友相遇
                                if teammateBattler.get_manhattan_distance_to(oppBattler) == 1:
                                    _shouldStay = False

                        #
                        # 如果敌人威胁我的位置它曾经到过（这种情况实际上包含了第三点）
                        #
                        # 先找到威胁我方坦克的位置
                        _enemyRiskySite = None # (x, y)
                        with map_.simulate_one_action(battler, realAction):
                            for _action in oppBattler.get_all_valid_move_actions():
                                with map_.simulate_one_action(oppBattler, _action):
                                    if battler.on_the_same_line_with(oppBattler):
                                        _enemyRiskySite = oppBattler.xy
                                        break

                        #assert _enemyRiskySite is not None # 一定会找到？

                        enemyAttackingRoute = oppBattler.get_shortest_attacking_route()
                        #
                        # 不在敌人的进攻路线上，这样才算是已经走过，否则可以认为他在晃墙？
                        # 5cec129e4742030582fac36d
                        #
                        if not _enemyRiskySite in enemyAttackingRoute:
                            with map_.auto_undo_revert() as counter:
                                while map_.revert(): # 回滚成功则 True
                                    counter.increase()
                                    if oppBattler.xy == _enemyRiskySite: # 他曾经到过这个地方
                                        _shouldStay = False
                                        break

                    if (_shouldStay
                        and player.has_status(Status.ENEMY_MAY_APPEAR_BEHIND_BRICK)
                        ): # 不能在这种情况下破墙！ 5cec129e4742030582fac36d
                        returnAction = Action.STAY
                        continue

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

                    #
                    # TODO:
                    #----------------
                    # 不要老是随便回头！这实在是太蠢了 5ced7a13641dd10fdcc7722b
                    # 有路也不是这么走啊 ...
                    #


                #
                # (inserted) 打破老是回头的僵局
                #
                # 尝试向着两边闪避 5ced9540641dd10fdcc79752
                #
                if (player.has_label(Label.ALWAYS_BACK_AWAY)
                    and not battler.is_in_our_site(include_midline=True) # 限制为严格地不在我方基地
                    ):
                    for action in battler.try_dodge(oppBattler):
                        _realAction = player.try_make_decision(action)
                        if not Action.is_stay(_realAction): # 可走的路线，那么直接闪避
                            player.set_status(Status.TRY_TO_BREAK_ALWAYS_BACK_AWAY)
                            player.remove_labels(Label.ALWAYS_BACK_AWAY) # 那么就打破了这个状态
                            realAction = _realAction # 并将闪避方向作为这回合的攻击方向
                            break

                # 否则继续攻击
                player.set_status(Status.KEEP_ON_MARCHING)
                returnAction = realAction
                raise OUTER_BREAK

            # endfor
        # endwith

        player.set_current_attacking_route(route) # 缓存攻击路线

        # 找到一个侵略性的行为
        if not Action.is_stay(returnAction):
            return returnAction

        # 否则返回 STAY
        player.set_status(Status.WAIT_FOR_MARCHING)
        return Action.STAY


#{ END }#