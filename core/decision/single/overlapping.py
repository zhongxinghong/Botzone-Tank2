# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 17:46:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 03:56:39

__all__ = [

    "OverlappingDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...utils import debug_print
from ...action import Action
from ...strategy.status import Status
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
                ): # 如果和一个带有跟随重叠标记的敌人僵持超过 3 回合，就把这个标记移除，因为它此时已经不是一个会和我马上打破重叠的敌人了
                oppPlayer.remove_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY) # 5ce3c990d2337e01c7a54b4c

            if (oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY)
                and Action.is_shoot(player.get_previous_action(back=1))
                and Action.is_shoot(oppPlayer.get_previous_action(back=1))
                # TODO: 是否有必要判断射击方向相同？
                ): # 如果和一个带有跟随重叠标记的敌人在同一回合采用射击的方式打破重叠，则对这个行为进一步标记
                oppPlayer.add_labels(Label.SIMULTANEOUSLY_SHOOT_TO_BREAK_OVERLAP)

            #
            # (inserted) 如果敌人带有立即打破重叠的标记，那么如果还能执行到这个地方，就意味着敌人
            # 上次打破重叠的方向是回防（如果是进攻，那么应该不会再有机会遭遇）
            #
            # 那么在此处重新进入重叠的时候，尝试将对手击杀
            #
            if not status == Status.DEFENSIVE: # 防御模式不触发？
                if (oppPlayer.has_label(Label.IMMEDIATELY_BREAK_OVERLAP_BY_MOVE)
                    and not player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY) # 上回合不重叠
                    ):
                    action = battler.get_next_attack_action()
                    if Action.is_move(action):
                        if battler.canShoot:
                            player.set_status(Status.READY_TO_BREAK_OVERLAP,
                                              Status.ATTEMPT_TO_KILL_ENEMY)
                            return action + 4

            #
            # (inserted) 观察到大多数人在遇到重叠时会选择直接无视对手，我们也可以学习一下这种决策
            # 但是目前不想让这个决策成为必须，希望它只在特定的状况下被触发。
            #
            # 对于非防御模式下，考虑这样三种情况：
            # -------------------------------------
            # 1. 假设我方当前进攻路线距离领先一步 ，如果对方主动打破重叠，这时，如果对方下一步可以闪避，
            #    而我方当前回合不饿能闪避，必须要还击（之所以必须要射击是因为我们考虑最坏的情况，假设
            #    对方这回合会还击，如果我方这时候不还击就会被打掉），假如对方这回合闪避了，并且恰好沿着进攻
            #    方向闪避，那么结束后对方将比我方领先一步，这时候即使再继续攻击，结局也很可能是输，
            #    因此这步可以考虑主动打破重叠
            #
            # 2. 假设我方当前进攻路线长度与敌方相同，假设对方主动打破重叠，假设对方可以闪避并且可以向着
            #    进攻方向闪避，那么对方很有可能比我方快一步，此时应该主动打破重叠。假如对方不能向着进攻方向
            #    闪避，那么认为敌人一定会还击，此时考虑我方下回合是否可以向着进攻方向闪避，如果不可以的话，
            #    我方就和对方差一步，处于劣势，那么就主动打破重叠。
            #
            # 3. 假设对方比我方领先一步，这种情况下多属于对方处在我方阵营，我方很可能会触发防御模式
            #    这种情况下就直接忽略掉吧
            #
            route1 = battler.get_shortest_attacking_route()
            route2 = oppBattler.get_shortest_attacking_route()
            _shouldActiveBreakOverlap = False
            _enemyAttackAction = Action.STAY
            if route1.is_not_found() or route2.is_not_found(): # 虽然应该不可能，但是还是判断一下
                pass
            else:
                _leadingLength = route2.length - route1.length # 我方领先步数
                debug_print(battler, _leadingLength)
                action = battler.get_next_attack_action(route1)
                if Action.is_shoot(action):
                    # TODO:
                    #   是否有必要考虑射击行为？
                    pass

                elif _leadingLength == 1: # 情况一

                    allRoutes = oppBattler.get_all_shortest_attacking_routes()
                    #
                    # 由于不同的路线下一步可能会走到相同的地方，而造成的结果相同
                    # 因此此处将相同的行为进行缓存，为了减少判断次数
                    _consideredActions = set()
                    for route in allRoutes:
                        _enemyAttackAction = oppBattler.get_next_attack_action(route)
                        if _enemyAttackAction in _consideredActions:
                            continue
                        _consideredActions.add(_enemyAttackAction)

                        if not Action.is_move(_enemyAttackAction):
                            # 只考虑移动行为，因为，假如对方当前回合射击，那么我方下回合可以移动
                            # 这时双方距离可以认为相等，很有可能平局
                            continue

                        # 提交地图模拟这步行为，这个时候双方应该均为僵持
                        with map_.simulate_one_action(oppBattler, _enemyAttackAction):

                            # 考虑下回合我方是否可以闪避
                            with player.create_snapshot():

                                # 确保这种情况下决策不会再运行到这里，因为此时将不再和敌人重叠，于是不会遇到递归无终点
                                action, _ = player.make_decision(signal=signal)
                                if action != battler.shoot_to(oppBattler):
                                    # 说明下回合我方可以闪避，那么就可以不管了
                                    continue

                            # 我方下回合不可以闪避，考虑敌人下回合是否可以闪避
                            with oppPlayer.create_snapshot():
                                action, _ = oppPlayer.make_decision()
                                if action != oppBattler.shoot_to(battler):
                                    # 说明下回合敌人可以闪避
                                    _shouldActiveBreakOverlap = True
                                    break

                elif _leadingLength == 0: # 情况二

                    allRoutes = oppBattler.get_all_shortest_attacking_routes()
                    _consideredActions = set()
                    for route in allRoutes:

                        _enemyAttackAction = oppBattler.get_next_attack_action(route)
                        if _enemyAttackAction in _consideredActions:
                            continue
                        _consideredActions.add(_enemyAttackAction)

                        if not Action.is_move(_enemyAttackAction):
                            # TODO:
                            #   仍然不考虑射击？为了防止无迭代终点？
                            continue

                        # 提交一步模拟，敌方应该比我方领先一步
                        with map_.simulate_one_action(oppBattler, _enemyAttackAction):

                            # 考虑下回合敌方是否可以闪避
                            with oppPlayer.create_snapshot():
                                action, _ = oppPlayer.make_decision()
                                if action != oppBattler.shoot_to(battler): # 敌方可以闪避
                                    _shouldActiveBreakOverlap = True
                                    break

                            # 对方下回合不可以闪避，那么考虑我方是否可以闪避
                            with player.create_snapshot():
                                action, _ = player.make_decision()
                                # TODO:
                                #   我方下回合可能是防御状态，这种情况下必定反击，判断不准确
                                #
                                #   不过问题其实不大，因为这样就会触发主动打破重叠
                                #
                                if action == battler.shoot_to(oppBattler): # 我方不能闪避
                                    _shouldActiveBreakOverlap = True
                                    break
                else:
                    # 其他情况，留作下一回合打破重叠
                    pass

            if _shouldActiveBreakOverlap:
                action = battler.get_next_attack_action(route1)
                if Action.is_move(action):
                    if player.is_safe_to_break_overlap_by_move(action, oppBattler):
                        player.set_status(Status.READY_TO_BREAK_OVERLAP)
                        player.set_status(Status.KEEP_ON_MARCHING)
                        return action
                elif Action.is_shoot(action):
                    #
                    # 假设下一步射击，考虑最糟糕的一种情况，那就是敌人同一回合主动打破重叠，移动到我方身后
                    # 而我方无法闪避，那么就有被敌人击杀的风险
                    #
                    _mayBeKilled = False
                    with map_.simulate_one_action(oppBattler, _enemyAttackAction):
                        with map_.simulate_one_action(battler, action):
                            if len(battler.try_dodge(oppBattler)) == 0: # 无法闪避！
                                _mayBeKilled = True

                    if not _mayBeKilled: # 在没有被击杀风险的情况下可以采用射击
                        return action


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


                            if player.is_safe_to_break_overlap_by_move(realAction, oppBattler):
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

                            # 首先先检查对方是否会跟随我
                            #--------------------------
                            # 1. 如果我方可以射击，对方不能射击，那么按照之前的经验，对方下回合会移动
                            #    这个时候尝试击杀
                            #
                            if oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY):
                                if battler.canShoot: # 这回合可以射击，则改为射击
                                    if (oppPlayer.has_label(Label.SIMULTANEOUSLY_SHOOT_TO_BREAK_OVERLAP)
                                        and oppBattler.canShoot # 如果带有这个标记，那么这回合就不要射击了，等待敌人打完这回合，
                                        ): # 下回合才有可能击杀 5ce50cd9d2337e01c7a6e45a
                                        player.set_status(Status.KEEP_ON_OVERLAPPING)
                                        return Action.STAY
                                    else: # 否则就考虑反身射击
                                        player.set_status(Status.READY_TO_BREAK_OVERLAP,
                                                          Status.ATTEMPT_TO_KILL_ENEMY) # 尝试击杀敌军
                                        return oppAction + 4
                                else:
                                    pass # 均不能射击，那么将判定为没有风险。那就一起移动

                            # 正常情况下选择堵路
                            #----------------------
                            if player.is_safe_to_break_overlap_by_move(oppAction, oppBattler): # 模仿敌人的移动方向
                                player.set_status(Status.READY_TO_BREAK_OVERLAP)
                                player.set_status(Status.READY_TO_BLOCK_ROAD) # 认为在堵路
                                return oppAction

                # 否则等待
                player.set_status(Status.READY_TO_BLOCK_ROAD)
                player.set_status(Status.KEEP_ON_OVERLAPPING)
                return Action.STAY


#{ END }#