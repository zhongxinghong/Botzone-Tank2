# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 17:03:07
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 14:33:06

__all__ = [

    "ActiveDefenseDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...global_ import np
from ...utils import outer_label, debug_print
from ...action import Action
from ...field import BrickField
from ...strategy.evaluate import evaluate_aggressive, estimate_route_similarity
from ...strategy.status import Status
from ...strategy.signal import Signal

#{ BEGIN }#

class ActiveDefenseDecision(SingleDecisionMaker):
    """
    主动防御策略
    -----------------------

    不要追击敌人，而是选择保守堵路策略！

    1. 对于路线差为 2 的情况，选择堵路，而非重叠
    2. 如果自己正常行军将会射击，那么判断射击所摧毁的块是否为敌人进攻路线上的块
       如果是，则改为移动或者停止

    """

    ACTIVE_DEFENSE_MIN_TRIGGER_TURNS = 2  # 前两回合结束前不要触发主动防御！


    def _make_decision(self):

        player  = self._player
        signal  = self._signal
        map_    = player._map
        tank    = player.tank
        battler = player.battler

        Tank2Player = type(player)
        BattleTank  = type(battler)


        oppTank = battler.get_nearest_enemy() # 从路线距离分析确定最近敌人
        oppBattler = BattleTank(oppTank)
        oppPlayer = Tank2Player(oppBattler)
        status = evaluate_aggressive(battler, oppBattler)
        player.set_status(status)

        if status == Status.DEFENSIVE:
            # 避免过早进入 DEFENSIVE 状态
            #----------------------------
            currentTurn = map_.turn
            if currentTurn < __class__.ACTIVE_DEFENSE_MIN_TRIGGER_TURNS and False: # 取消主动防御轮数限制？
                player.remove_status(Status.DEFENSIVE)
                player.set_status(Status.AGGRESSIVE)   # 前期以侵略性为主
            else:
                # 如果是距离为 2
                #----------------
                # 由于两者相对的情况在前面的 encount enemy 时会被处理，这里如果遇到这种情况
                # 那么说明两者是出于不相对的对角线位置。
                #
                _route = battler.get_route_to_enemy_by_move(oppBattler)
                if _route.is_not_found():
                    _route = battler.get_route_to_enemy_by_move(oppBattler, block_teammate=False)
                assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                assert _route.length > 0, "unexpected overlapping enemy"
                if _route.length == 2:
                    #
                    # 此时应该考虑自己是否正处在敌方的进攻的必经之路上
                    # 如果是这样，那么考虑不动，这样最保守
                    # 否则在合适的回合冲上去挡路
                    #
                    # 判定方法是将己方坦克分别视为空白和钢墙，看对方的最短路线长度是否有明显延长
                    # 如果有，那么就堵路
                    #
                    # 需要能够正确应对这一局的情况 5cd356e5a51e681f0e921453
                    # TODO:
                    #   事实上这一局敌方不管往左还是往右，都是8步，因此这里会判定为不堵路，所以就会主动重叠
                    #   但是，左右两边的走法是不一样的，往左走必定会走不通，左右的8步并不等价，这里需要还需要
                    #   进一步的分析路线的可走性
                    #
                    # TODO:
                    #   事实上这样不一定准确，因为如果敌人前面有一个土墙，那么他可以先打掉土墙
                    #   然后继续前移，这样敌方就可以选择继续往前移动
                    #
                    enemyAttackRoute1 = oppBattler.get_shortest_attacking_route(ignore_enemies=True, bypass_enemies=False)
                    enemyAttackRoute2 = oppBattler.get_shortest_attacking_route(ignore_enemies=False, bypass_enemies=True)
                    if enemyAttackRoute2.length > enemyAttackRoute1.length: # 路线增长，说明是必经之路
                        player.set_status(Status.ACTIVE_DEFENSIVE)
                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY

                    #
                    # 虽然路线长度相同，但是路线的可走性不一定相同，这里先衡量对方当前路线的可走性
                    # 如果本回合我方等待，敌人向前移动，那么敌方只有在能够不向原来位置闪避的情况下
                    # 才算是我堵不住他的路，否则仍然视为堵路成功 5cd356e5a51e681f0e921453
                    #
                    x0, y0 = oppBattler.xy # 保存原始坐标
                    enemyMoveAction = oppBattler.get_next_attacking_action(enemyAttackRoute1)
                    # ssert Action.is_move(enemyMoveAction) # 应该是移动
                    _shouldStay = False
                    with map_.simulate_one_action(oppBattler, enemyMoveAction):
                        if battler.get_manhattan_distance_to(oppBattler) == 1: # 此时敌方与我相邻
                            _shouldStay = True # 这种情况才是真正的设为 True 否则不属于此处应当考虑的情况
                            for enemyDodgeAction in oppBattler.try_dodge(battler):
                                with map_.simulate_one_action(oppBattler, enemyDodgeAction):
                                    if oppBattler.xy != (x0, y0): # 如果敌人移动后可以不向着原来的位置闪避
                                        _shouldStay = False # 此时相当于不能堵路
                                        break
                    if _shouldStay:
                        player.set_status(Status.ACTIVE_DEFENSIVE)
                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY

                    #
                    # 否则自己不处在敌方的必经之路上，考虑主动堵路
                    #
                    if (not oppBattler.canShoot # 对方这回合不能射击
                        or (Action.is_stay(oppPlayer.get_previous_action(back=1))
                            and Action.is_stay(oppPlayer.get_previous_action(back=2))
                            ) # 或者对方等待了两个回合，视为没有危险
                        ):    # 不宜只考虑一回合，否则可能会出现这种预判错误的情况 5cdd894dd2337e01c79e9bed
                        for moveAction in battler.get_all_valid_move_action():
                            with map_.simulate_one_action(battler, moveAction):
                                if battler.xy in enemyAttackRoute1: # 移动后我方坦克位于敌方坦克进攻路线上
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return moveAction

                        # 我方的移动后仍然不会挡敌人的路？？
                        for moveAction in battler.get_all_valid_move_action(middle_first=True): # 中路优先
                            with map_.simulate_one_action(battler, moveAction):
                                if battler.get_manhattan_distance_to(oppBattler) == 1: # 如果移动后与敌人相邻
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return moveAction

                        # 否则，就是和敌人接近的连个方向上均为不可走的！
                        # 那么让后续的逻辑进行处理
                        pass

                    '''
                    if (
                            # 可能是主动防御但是为了防止重叠而等待
                            (
                                player.has_status_in_previous_turns(Status.ACTIVE_DEFENSIVE, turns=1)
                                and player.has_status_in_previous_turns(Status.READY_TO_BLOCK_ROAD, turns=1)
                                and Action.is_stay(player.get_previous_action(back=1))
                            )

                        or
                            # 可能是为了防止被杀而停止
                            (
                                player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED)
                                and Action.is_stay(player.get_previous_action(back=1))
                            )

                        ):
                        oppPlayer = Tank2Player(oppBattler)
                        if Action.is_stay(oppPlayer.get_previous_action(back=1)): # 对方上回合在等待
                            #
                            # 但是遇到这种情况就非常尴尬 5cd356e5a51e681f0e921453
                            #
                            # 需要再判断一下是否有必要上前堵路
                            #
                            _shouldMove = False
                            x1, y1 = oppBattler.xy
                            x2, y2 = _route[1].xy # 目标位置
                            enemyAttackRoute = oppBattler.get_shortest_attacking_route()
                            if (x2, y2) in enemyAttackRoute: # 下一步移动为进攻路线
                                enemyMoveAction = Action.get_move_action(x1, y1, x2, y2)
                                with map_.simulate_one_action(oppBattler, enemyMoveAction):
                                    for enemyDodgeAction in oppBattler.try_dodge(battler): # 如果敌人上前后可以闪避我
                                        route1 = oppBattler.get_shortest_attacking_route()
                                        with map_.simulate_one_action(oppBattler, enemyDodgeAction):
                                            route2 = oppBattler.get_shortest_attacking_route()
                                            if route2.length <= route1.length: #　并且闪避的路线不是原路返回
                                                _shouldMove = True
                                                break

                            #
                            # 真正的值得堵路的情况
                            #
                            if _shouldMove:
                                x1, y1 = battler.xy
                                x2, y2 = _route[1].xy # 跳过开头
                                moveAction = Action.get_move_action(x1, y1, x2, y2)
                                if map_.is_valid_move_action(battler, moveAction): # 稍微检查一下，应该本来是不会有错的
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return moveAction

                    #
                    # 否则选择不要上前和敌人重叠，而是堵路
                    #
                    player.set_status(Status.ACTIVE_DEFENSIVE)
                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                    return Action.STAY'''

                # endif


                # 转向寻找和敌方进攻路线相似度更高的路线
                #--------------------------------------
                #
                enemyAttackRoute = oppBattler.get_shortest_attacking_route()
                closestAttackRoute = max( battler.get_all_shortest_attacking_routes(delay=3), # 允许 3 步延迟
                                            key=lambda r: estimate_route_similarity(r, enemyAttackRoute) ) # 相似度最大的路线

                #
                # 判断下一步是否可以出现在敌人的攻击路径之上 5cd31d84a51e681f0e91ca2c
                #-------------------------------
                # 如果可以，就移动过去
                #
                x1, y1 = battler.xy
                for x3, y3 in battler.get_surrounding_empty_field_points():
                    if (x3, y3) in enemyAttackRoute:
                        moveAction = Action.get_move_action(x1, y1, x3, y3)
                        assert map_.is_valid_move_action(battler, moveAction)
                        willMove = False # 是否符合移动的条件
                        realAction = player.try_make_decision(moveAction)
                        if Action.is_move(realAction):
                            willMove = True
                        elif player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1): # 打破僵局
                            oppPlayer = Tank2Player(player.get_risky_enemy())
                            if (oppPlayer.battler.canShoot # 当回合可以射击
                                and not oppPlayer.has_status_in_previous_turns(Status.RELOADING) # 上回合也可以射击
                                ): # 说明敌人大概率不打算攻击我
                                willMove = True

                        #
                        # 符合了移动的条件
                        # 但是还需要检查移动方向
                        # 不能向着远离敌人的方向移动，不然就会后退 ... 5cd33351a51e681f0e91da39
                        #
                        if willMove:
                            distance1 = battler.get_manhattan_distance_to(oppBattler)
                            with map_.simulate_one_action(battler, moveAction):
                                distance2 = battler.get_manhattan_distance_to(oppBattler)
                                if distance2 > distance1: # 向着远处移动了
                                    pass
                                else:
                                    # 添加一个限制，必须要移动后出现在敌人的附近
                                    # 否则约束过弱，容易导致前期乱跑的情况 5cd39434a51e681f0e924128
                                    #
                                    for enemy in oppBattler.get_enemies_around():
                                        if enemy is tank:
                                            player.set_status(Status.ACTIVE_DEFENSIVE)
                                            player.set_status(Status.READY_TO_BLOCK_ROAD)
                                            return moveAction


                attackAction = battler.get_next_attacking_action(closestAttackRoute)
                realAction = player.try_make_decision(attackAction)

                #
                # 判断自己的下一步是否为敌人开路
                #-------------------------
                # 如果自己下一个行为是射击，然后所射掉的块为敌人进攻路线上的块
                # 那么将这个动作转为移动或者停止
                #
                # TODO:
                #   这个动作是有条件的，通常认为是，块就处在敌人的周围，我将块打破后
                #   敌人有炮，我不能马上移到块的，这样就可能让敌人过掉，在这种情况下避免开炮
                #
                #   TODO:
                #     不能被过掉的情况不准确！只有不再在同一直线的情况下才需要判断 5ce444a8d2337e01c7a5eaea
                #     如果两者处在同一条直线，假如双方都射击，那么下一回合就直接相遇，并不会出现被对方过掉的情况
                #
                if not battler.on_the_same_line_with(oppBattler):
                    if Action.is_shoot(realAction):
                        fields = battler.get_destroyed_fields_if_shoot(realAction)
                        if len(fields) == 1:
                            field = fields[0]
                            if isinstance(field, BrickField):
                                enemyAttackRoute = oppBattler.get_shortest_attacking_route()
                                if enemyAttackRoute.has_block(field): # 打掉的 Brick 在敌人进攻路线上
                                    #
                                    # 再尝试模拟，是否会导致上述情况
                                    #
                                    # TODO:
                                    #   还需要分析敌人的行为!
                                    #
                                    _dontShoot = False

                                    with map_.simulate_one_action(battler, realAction):
                                        moveAction = realAction - 4
                                        with map_.simulate_one_action(battler, moveAction): # 再走一步
                                            # 敌方模拟两步
                                            with outer_label() as OUTER_BREAK:
                                                for action in oppBattler.get_all_valid_actions():
                                                    with map_.simulate_one_action(oppBattler, action):
                                                        for action in oppBattler.get_all_valid_actions():
                                                            with map_.simulate_one_action(oppBattler, action):

                                                                if battler.destroyed:
                                                                    _dontShoot = True
                                                                else:
                                                                    for enemy in oppBattler.get_enemies_around():
                                                                        if enemy is tank:
                                                                            _dontShoot = True
                                                                if _dontShoot:
                                                                    raise OUTER_BREAK

                                    if _dontShoot:
                                        player.set_status(Status.ACTIVE_DEFENSIVE)
                                        return player.try_make_decision(moveAction) # 移动/停止

                # 否则直接采用主动防御的进攻策略
                #
                # TODO:
                #   这是个糟糕的设计，因为这相当于要和下方的进攻代码重复一遍
                #
                if battler.is_in_our_site():  # 只有在我方地盘的时候才触发
                    #
                    # 首先实现禁止随便破墙
                    #
                    if Action.is_shoot(realAction):
                        #
                        # 敌人处在墙后的水平路线上，并且与墙的间隔不超过 1 个空格 5cd33a06a51e681f0e91de95
                        # 事实上 1 个空格是不够的！ 5cd35e08a51e681f0e92182e
                        #
                        enemy = battler.get_enemy_behind_brick(realAction, interval=-1)
                        if enemy is not None:
                            player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)
                            player.set_status(Status.ACTIVE_DEFENSIVE)
                            return Action.STAY
                        #
                        # 敌人下一步可能移到墙后面
                        #
                        x1, y1 = oppBattler.xy
                        for x2, y2 in oppBattler.get_surrounding_empty_field_points():
                            moveAction = Action.get_move_action(x1, y1, x2, y2)
                            assert map_.is_valid_move_action(oppBattler, moveAction)
                            with map_.simulate_one_action(oppBattler, moveAction):
                                if battler.get_enemy_behind_brick(realAction, interval=-1) is not None: # 此时如果直接出现在墙的后面
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return Action.STAY


                    if Action.is_stay(realAction):
                        # (inserted) 主动打破僵局：因为遇到敌人，为了防止被射杀而停留
                        # 注：
                        #   这段代码复制自下方的侵略模式
                        #--------------------------
                        if Action.is_move(attackAction):
                            if player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1): # 即将停留第二回合
                                oppPlayer = Tank2Player(oppBattler)
                                if (Action.is_move(oppPlayer.get_previous_action(back=1))
                                    and battler.get_manhattan_distance_to(oppBattler) == 2
                                    ): # 这种情况对应着对方刚刚到达拐角处，这种情况是有危险性的，因此再停留一回合 5cd4045c86d50d05a00840e1
                                    pass
                                elif oppBattler.canShoot: # 当回合可以射击，并且我上回合停留，因此敌人上回合可以射击
                                    # 说明敌人大概率不打算攻击我
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return attackAction

                        player.set_status(Status.PREVENT_BEING_KILLED) # 否则标记为防止被杀，用于上面的触发

                    player.set_status(Status.ACTIVE_DEFENSIVE)
                    return realAction

#{ END }#