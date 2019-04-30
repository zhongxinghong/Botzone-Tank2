# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 00:35:10
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 00:46:16
"""
游戏玩家，操作着一架坦克，充当决策者

"""

__all__ = [

    "Tank2Player",

    ]

from .utils import debug_print
from .action import Action
from .field import BrickField, WaterField, EmptyField, TankField, BaseField
from .tank import BattleTank
from .strategy.utils import is_block_in_route
from .strategy.bfs import find_shortest_route_for_move, get_route_length, INFINITY_ROUTE_LENGTH,\
                    DEFAULT_BLOCK_TYPES
from .strategy.estimate import assess_aggressive, AGGRESSIVE_STATUS, DEFENSIVE_STATUS, STALEMATE_STATUS


#{ BEGIN }#

class Player(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
        raise NotImplementedError


class Tank2Player(Player):

    def __init__(self, tank, map, past_actions):
        self._tank = tank
        self._map = map
        self._battler = BattleTank(tank, map)
        self._teammate = None
        self._opponents = None
        self._pastActions = past_actions

    @property
    def side(self):
        return self._tank.side

    @property
    def id(self):
        return self._id

    @property
    def defeated(self):
        return self._tank.destroyed

    @property
    def battler(self):
        return self._battler

    @property
    def tank(self):
        return self._tank


    def set_teammate(self, player):
        """
        设置队友

        Input:
            - player    Tank2Player    队友
        """
        assert isinstance(player, self.__class__) and player.side == self.side
        self._teammate = player

    def set_opponents(self, opponents):
        """
        设置对手

        Input:
            - opponents    [Tank2Player]    对手们
        """
        for player in opponents:
            assert isinstance(player, self.__class__) and player.side != self.side
        self._opponents = opponents

    def get_past_actions(self):
        return self._pastActions


    def is_safe_action(self, action):
        """
        评估该这个决策是否安全

        Return:
            - issafe   bool   安全
        """
        tank    = self._tank
        map_    = self._map
        battler = self._battler

        if not map_.is_valid_action(tank, action): # 先检查是否为有效行为
            return False

        if Action.is_stay(action):
            return True

        # 移动情况下有一种可能的风险
        #--------------------------
        # 1. 需要考虑移动后恰好被对方打中
        # -------------------------
        if Action.is_move(action):
            oppBattlers = [BattleTank(oppTank, map_) for oppTank in map_.tanks[1 - tank.side]]
            riskFreeOpps = []
            for oppBattler in oppBattlers:
                if not oppBattler.canShoot: # 对手本回合无法射击，则不必担心
                    riskFreeOpps.append(oppBattler)
            map_.simulate_one_action(tank, action) # 提交地图模拟情况
            for oppBattler in oppBattlers:
                if oppBattler.destroyed:
                    continue
                elif oppBattler in riskFreeOpps:
                    continue
                for enemy in oppBattler.get_enemies_around():
                    if enemy is tank:
                        map_.revert()
                        return False
            map_.revert()

        # 射击情况下有两种可能的危险
        #--------------------------
        # 1. 打破一堵墙，然后敌人在后面等着
        # 2. 身边没有闪避的机会，打破一堵墙，对方刚好从旁路闪出来
        #---------------------------
        if Action.is_shoot(action):
            map_.simulate_one_action(tank, action) # 提交地图模拟情况
            # TODO:
            #   只模拟一个坦克的行为并不能反映真实的世界，因为敌方这回合很有可能射击
            #   那么下回合它就无法射击，就不应该造成威胁
            for oppTank in map_.tanks[1 - tank.side]:
                if oppTank.destroyed:
                    continue
                oppBattler = BattleTank(oppTank, map_)
                for oppAction in range(Action.STAY, Action.MOVE_LEFT + 1): # 任意移动行为
                    if not map_.is_valid_action(oppTank, oppAction):
                        continue
                    map_.simulate_one_action(oppTank, oppAction)
                    for enemy in oppBattler.get_enemies_around():
                        if enemy is tank: # 敌方原地不动或移动一步后，能够看到该坦克
                            # 还可以尝试回避
                            actions = battler.try_dodge(enemy)
                            if len(actions) == 0: # 无法回避，危险行为
                                map_.revert()
                                map_.revert() # 再回退外层模拟
                                return False
                    map_.revert()
            map_.revert()

        return True # 默认安全？


    def try_make_decision(self, action, instead=Action.STAY):
        """
        用这个函数提交决策
        如果这个决策被判定是危险的，那么将提交 instead 行为
        """
        if not Action.is_valid(action):
            return instead
        elif not self.is_safe_action(action):
            return instead
        else:
            return action


    def make_decision(self):
        """
        做决策，返回一个行为的编号

        Return:
            - action   int   行为编号，如果已经输了，则返回 Action.INVALID
        """
        if self.defeated:
            return Action.INVALID

        tank    = self._tank
        map_    = self._map
        battler = self._battler

        ## 观察队友情况

        ## 周围有敌人时
        aroundEnemies = battler.get_enemies_around()
        if len(aroundEnemies) > 0:
            if len(aroundEnemies) > 1: # 两个敌人，尝试逃跑
                oppBattlers = [BattleTank(t, map_) for t  in aroundEnemies]
                if all( oppBattler.canShoot for oppBattler in oppBattlers ):
                    # 如果两者都有弹药，有凉了 ...
                    # raise NotImplementedError
                    return self.try_make_decision(battler.shoot_to(oppBattlers[0]),
                                self.try_make_decision(battler.shoot_to(oppBattlers[1])),
                                    self.try_make_decision(battler.get_next_attack_action()))
                    return Action.STAY
                else:
                    for oppBattler in oppBattlers:
                        if oppBattler.canShoot:
                            actions = battler.try_dodge(oppBattler)
                            if len(actions) == 0: # 不能闪避
                                return self.try_make_decision(battler.shoot_to(oppBattler))
                            elif actions == 1:
                                return self.try_make_decision(actions[0])
                            else:
                                return self.try_make_decision(actions[0],
                                            self.try_make_decision(actions[1]))
            else: # len(aroundEnemies) == 1:
                oppTank = aroundEnemies[0]
                oppBattler = BattleTank(oppTank, map_)

                # 根据当时的情况，评估侵略性
                status = assess_aggressive(battler, oppBattler)

                # 侵略模式
                #----------
                # 1. 优先拆家
                # 2. 只在必要的时刻还击
                # 3. 闪避距离不宜远离拆家路线
                if status == AGGRESSIVE_STATUS:
                    if not oppBattler.canShoot:
                        # 如果能直接打死，那当然是不能放弃的！！
                        if len( oppBattler.try_dodge(battler) ) == 0: # 必死
                            return self.try_make_decision(battler.shoot_to(oppBattler),
                                        self.try_make_decision(battler.get_next_attack_action()))
                        attackAction = battler.get_next_attack_action() # 其他情况，优先进攻，不与其纠缠
                        action = self.try_make_decision(attackAction)
                        if Action.is_stay(action): # 存在风险
                            if Action.is_stay(attackAction): # 原本就是停留的
                                return action
                            elif Action.is_move(attackAction):
                                # 原本移动或射击，因为安全风险而变成停留，这种情况可以尝试射击，充分利用回合数
                                fields = battler.get_destroyed_fields_if_shoot(attackAction)
                                route = battler.get_shortest_attacking_route()
                                for field in fields:
                                    if is_block_in_route(field, route): # 为 block 对象，该回合可以射击
                                        return self.try_make_decision(battler.shoot_to(field), action)
                                return action
                            else:
                                return action # 不然就算了
                        return self.try_make_decision(battler.get_next_attack_action(),
                                    self.try_make_decision(battler.shoot_to(oppBattler)))
                    else: # 对方有炮弹，先尝试闪避，如果闪避恰好和侵略路线一致，就闪避，否则反击
                        defenseAction = battler.shoot_to(oppBattler) # 不需检查安全性，这就是最安全的行为！
                        actions = battler.try_dodge(oppTank)
                        attackAction = battler.get_next_attack_action()
                        for action in actions:
                            if Action.is_move(action) and Action.is_same_direction(action, attackAction):
                                return self.try_make_decision(action, defenseAction)
                        return defenseAction

                # 防御模式
                #----------
                # 1. 优先对抗，特别是当对方必死的时候
                # 2. 否则等待
                # 3. TODO: 如何拖住对方？或者反杀？
                #
                # elif status == DEFENSIVE_STATUS:
                else: # status == DEFENSIVE_STATUS or status == STALEMATE_STATUS:
                    attackAction = self.try_make_decision(battler.get_next_attack_action()) # 默认的侵略行为
                    if not oppBattler.canShoot: # 对方不能射击，则进攻
                        # TODO: 或者前进？？？
                        if len( oppBattler.try_dodge(battler) ) == 0:
                            if battler.canShoot: # 必死
                                return battler.shoot_to(oppBattler)
                            else: # 对方通常会闪避，这时候判断和对方的距离，考虑是否前进
                                route = battler.get_route_to_enemy_by_movement(oppBattler)
                                routeLen = get_route_length(route)
                                assert routeLen > 0, "unexpected overlapping enemy"
                                if routeLen == 1: # 和对方相邻
                                    return Action.STAY # 原地等待，对方就无法通过
                                elif routeLen == 2: # 和对方相隔一个格子
                                    # TODO: 可以前进也可以等待，这个可能需要通过历史行为分析来确定
                                    return Action.STAY # 原地等待，对方就必定无法通过
                                else: # if routeLen > 2: # 和对方相隔两个以上的格子
                                    # 有可能是水路
                                    x1, y1 = battler.xy
                                    x2, y2 = oppBattler.xy
                                    action = Action.get_action(x1, y1, x2, y2)
                                    if map_.is_valid_move_action(tank, action):
                                        # 在防止别的坦克从旁边偷袭的情况下，往前移动
                                        return self.try_make_decision(action)
                                    else: #可能是隔着水路
                                        return Action.STAY
                        else: # 对方可以闪避，可以认为对方大概率会闪避，除非是无脑bot
                            # 在这种情况下仍然要优先射击，因为如果对方不闪避，就会被打掉
                            # 如果对方闪避，对方的侵略路线就会加长来去的两步（假设对方最优的
                            # 路线是通过我方坦克，且没有第二条可选路线），因此下一步很可能会
                            # 回来（因为那个时候我方坦克没有炮），在这种情况下我方坦克可能以
                            # 警戒的状态原地不动，因此最后局面又回到原始的样子
                            if battler.canShoot:
                                return battler.shoot_to(oppBattler)
                            else: # 我方也不能射击，这时候对方可能会前移
                                route = battler.get_route_to_enemy_by_movement(oppBattler)
                                routeLen = get_route_length(route)
                                if routeLen == 1: # 和对方相邻
                                    return Action.STAY # 原地等待
                                elif routeLen == 2: # 和对方相差一格，这个时候需要注意
                                    # TODO:
                                    # 如果对方绕路呢？
                                    return Action.STAY # 原地等待最保守
                    else: # 对方可以射击
                        if battler.canShoot: # 优先反击
                            return battler.shoot_to(oppBattler)
                        else: # 只好闪避
                            actions = battler.try_dodge(oppBattler)
                            if len(actions) == 0: # ??? 这种情况在预警的时候就要知道了
                                return attackAction # 随便打打吧 ...
                            elif len(actions) == 1:
                                return self.try_make_decision(actions[0], attackAction)
                            else: # len(actions) == 2:
                                return self.try_make_decision(actions[0],
                                            self.try_make_decision(actions[1]),
                                                attackAction)

                # 僵持模式？
                #--------------
                # 双方进攻距离相近，可能持平
                # # TODO:
                #   观察队友？支援？侵略？
                # 1. 优先防御
                # 2. ....
                #
                # elif status == STALEMATE_STATUS:



        # 与敌人重合时，一般只与一架坦克重叠
        #--------------------------
        # 1. 根据路线评估侵略性，确定采用进攻策略还是防守策略
        # 2.
        #
        if battler.has_overlapping_enemy():
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank, map_)

            # 评估进攻路线长度，以确定采用保守策略还是入侵策略
            status = assess_aggressive(battler, oppBattler)

            # 侵略模式
            #-----------
            # 1. 直奔对方基地，有机会就甩掉敌人。
            if status == AGGRESSIVE_STATUS:
                if not oppBattler.canShoot: # 对方不能射击，对自己没有风险
                    # 尝试移动
                    #
                    # TODO:
                    #   还可以写得更加侵略性一些，比如为前方开路
                    action = battler.get_next_attack_action()
                    if Action.is_move(action):
                        return self.try_make_decision(action,
                                    self.try_make_decision(action + 4)) # 否则尝试开炮
                    else: # 射击或停留
                        return self.try_make_decision(action)
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
                if not oppBattler.canShoot: # 对方不能射击，对自己没有风险，那么就回头堵路！
                    # 假设对方采用相同的侵略性算法
                    # TODO:
                    #   还可以根据历史行为分析是否是进攻性的
                    oppAction = oppBattler.get_next_attack_action()
                    if Action.is_move(oppAction):
                        # TODO:
                        #   回头堵路并不一定是最好的办法因为对于无脑 bot
                        #   没有办法射击就前进，如果我恰好后退，就相当于对方回退了一步
                        #   这种情况下应该考虑回头开炮！
                        return self.try_make_decision(oppAction)
                    else:
                        return Action.STAY # 否则等待
                else: # 对方可以攻击，等待会比较好
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


        # 没有遭遇任何敌人
        #-----------------
        # 1. 进攻
        # 2. 如果存在安全风险，尝试采用射击代替移动
        attackAction = battler.get_next_attack_action()
        action = self.try_make_decision(attackAction)
        if Action.is_stay(action): # 存在风险
            if Action.is_move(attackAction):
                # 原本的移动，现在变为停留，则尝试射击
                # TODO: 如果不在线路上，但是能够打掉东西，事实上也可以尝试射击？
                fields = battler.get_destroyed_fields_if_shoot(attackAction)
                route = battler.get_shortest_attacking_route()
                for field in fields:
                    if is_block_in_route(field, route): # 为 block 对象，该回合可以射击
                        return self.try_make_decision(battler.shoot_to(field), action)
        return action

#{ END }#