# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 00:35:10
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-03 05:39:38
"""
游戏玩家，操作着一架坦克，充当单人决策者

"""

__all__ = [

    "Tank2Player",

    ]

from .const import DEBUG_MODE, SIMULATOR_ENV
from .utils import debug_print
from .action import Action
from .field import BrickField, WaterField, EmptyField, TankField, BaseField
from .tank import BattleTank
from .strategy.signal import Signal
from .strategy.status import Status
from .strategy.utils import is_block_in_route
from .strategy.search import find_shortest_route_for_move, get_route_length, INFINITY_ROUTE_LENGTH
from .strategy.estimate import assess_aggressive, MINIMAL_TURNS_FOR_ACTIVE_DEFENSIVE_DECISION


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
        self._team = None
        self._teammate = None
        self._opponents = None
        # self._pastActions = past_actions
        self._status = set() #　当前的状态，可以有多个

    def __repr__(self):
        return "%s(%d, %d, %d, %d)" % (
                self.__class__.__name__, self.side, self.id,
                self._tank.x, self._tank.y)

    @property
    def side(self):
        return self._tank.side

    @property
    def id(self):
        return self._tank.id

    @property
    def defeated(self):
        return self._tank.destroyed

    @property
    def tank(self):
        return self._tank

    @property
    def battler(self):
        return self._battler

    @property
    def team(self):
        return self._team

    @property
    def teammate(self):
        return self._teammate


    def set_team(self, team):
        self._team = team

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

    def get_status(self):
        return self._status

    def set_status(self, *status):
        """
        添加一个或多个状态
        """
        for _status in status:
            self._status.add(_status)

    def remove_status(self, status):
        """
        删除状态
        """
        self._status.discard(status) # remove_if_exists

    def clear_status(self):
        """
        情况所有状态
        """
        self._status.clear()

    def has_status(self, status):
        """
        检查是否存在某种状态
        """
        return status in self._status

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
            oppBattlers = [ player.battler for player in self._opponents ]
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
                oppBattler = BattleTank(oppTank)
                for oppAction in Action.MOVE_ACTIONS: # 任意移动行为
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


    def is_safe_to_close_to_this_enemy(self, oppBattler):
        """
        下回合接近某个敌人是否安全？
        ---------------------------
        用于双方相遇 (且敌人无法射击)，我方试图接近他的时候

        这种情况下需要判断周围是否有敌人攻击我

        """
        tank = self._tank
        map_ = self._map
        battler = self._battler

        if oppBattler.canShoot: # 可以射击，必定不安全，还是检查一下
            return False

        action = battler.move_to(oppBattler)

        if map_.is_valid_move_action(tank, action):
            for _oppBattler in [ player.battler for player in self._opponents ]: # 找到另一个敌人
                if _oppBattler.destroyed: # 输了就不算
                    continue
                if _oppBattler is oppBattler: # 排除目前这个敌人
                    continue
                if not _oppBattler.canShoot: # 本回合不能攻击的不算
                    continue
                # 开始模拟，反正就一架坦克
                map_.simulate_one_action(tank, action)
                for enemy in _oppBattler.get_enemies_around():
                    if enemy is tank: # 我方坦克将出现在它旁边，并且它可以射击
                        map_.revert()
                        return False # 可能被偷袭
                map_.revert()
            else: # 此处判断不会被偷袭
                return True
        else:
            return False # 不能移动，当然不安全 ...


    def is_safe_to_break_overlap_by_movement(self, action, oppBattler):
        """
        在不考虑和自己重叠的敌人的情况下，判断采用移动的方法打破重叠是否安全
        此时将敌人视为不会攻击，然后考虑另一个敌人的攻击
        """
        tank = self._tank
        map_ = self._map
        if not map_.is_valid_move_action(tank, action): # 还是检查一下，不要出错
            return False
        _oppBattlers = [ player.battler for player in self._opponents ]
        for _oppBattler in _oppBattlers:
            if _oppBattler.destroyed: # 跳过已经输了的
                continue
            if not _oppBattler.canShoot: # 另一个对手不能射击
                continue
            if _oppBattler is oppBattler: # 不考虑和自己重叠的这个坦克
                continue
            map_.simulate_one_action(tank, action) # 提交模拟
            for enemy in _oppBattler.get_enemies_around():
                if enemy is tank: # 不安全，可能有风险
                    map_.revert()
                    return False
            map_.revert()
        return True # 否则是安全的


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

    def make_decision(self, signal=Signal.NONE):
        """
        make_decision 的修饰

        - 清除所有旧有状态
        - 统一处理回复信号
        """
        self.clear_status() # 先清除所有的状态

        res = self._make_decision(signal)

        if isinstance(res, (tuple, list)) and len(res) == 2:
            outputSignal = res[1]
            action = res[0]
        else:
            outputSignal = Signal.NONE
            action = res

        inputSignal = signal

        if inputSignal != Signal.NONE and outputSignal == Signal.NONE:
            outputSignal = Signal.UNHANDLED # 没有回复团队信号

        return ( action, outputSignal )


    def _make_decision(self, signal):
        """
        真正的 make_decision 决策下一步的行为

        Input:
            - signal   int   团队信号

        Return:
            - action   int   行为编号，如果已经输了，则返回 Action.INVALID
        """
        teammate = self._teammate
        tank     = self._tank
        map_     = self._map
        battler  = self._battler

        if self.defeated:
            self.set_status(Status.DIED)
            return Action.INVALID

        if not battler.canShoot:
            self.set_status(Status.REALODING)

        #///////////#
        #  无脑进攻  #
        #///////////#


        # 首先当然是拆基地！！
        #----------------------
        # 无脑进攻区域
        # ---------------------
        if battler.is_face_to_enemy_base() and battler.canShoot:
            self.set_status(Status.READY_TO_ATTACK_BASE) # 特殊状态
            return battler.get_next_attack_action() # 必定是射击 ...


        #/////////////#
        #  预警或反击  #
        #/////////////#

        # 周围有敌人时
        #-------------------
        aroundEnemies = battler.get_enemies_around()
        if len(aroundEnemies) > 0:
            self.set_status(Status.ENCOUNT_ENEMY)
            if len(aroundEnemies) > 1: # 两个敌人，尝试逃跑
                assert len(aroundEnemies) == 2
                # 首先判断是否为真正的双人夹击
                enemy1, enemy2 = aroundEnemies
                x, y = tank.xy
                x1, y1 = enemy1.xy
                x2, y2 = enemy2.xy
                if x1 == x2 == x:
                    if (y > y1 and y > y2) or (y < y1 and y < y2):
                        self.set_status(Status.ENCOUNT_ONE_ENEMY)
                        pass # 实际可视为一个人
                elif y1 == y2 == y:
                    if (x > x1 and x > x2) or (x < x1 and x < x2):
                        self.set_status(Status.ENCOUNT_ONE_ENEMY)
                        pass
                else: # 真正的被夹击
                    self.set_status(Status.ENCOUNT_TWO_ENEMY)
                    oppBattlers = [ BattleTank(t) for t  in aroundEnemies ]
                    if all( oppBattler.canShoot for oppBattler in oppBattlers ):
                        # 如果两者都有弹药，可能要凉了 ...
                        self.set_status(Status.DYING)
                        if battler.canShoot:
                            # TODO: 这种情况下有选择吗？
                            self.set_status(Status.READY_TO_FIGHT_BACK)
                            return battler.shoot_to(enemy1) # 随便打一个？
                    elif all( not oppBattler.canShoot for oppBattler in oppBattlers ):
                        # 均不能进攻的话，优先闪避到下回合没有敌人的位置（优先考虑拆家方向）
                        firstMoveAction = tuple()
                        attackAction = battler.get_next_attack_action()
                        if Action.is_move(attackAction): # 如果是移动行为
                            firstMoveAction = ( attackAction, )
                        for action in firstMoveAction + Action.MOVE_ACTIONS:
                            if map_.is_valid_move_action(tank, action):
                                map_.simulate_one_action(tank, action)
                                if len( battler.get_enemies_around() ) < 2: # 一个可行的闪避方向
                                    map_.revert()
                                    self.set_status(Status.READY_TO_DODGE)
                                    return action
                                map_.revert()
                        # 均不能闪避，应该是处在狭道内，则尝试任意攻击一个
                        if battler.canShoot:
                            # TODO: 是否有选择？
                            self.set_status(Status.READY_TO_FIGHT_BACK)
                            return battler.shoot_to(enemy1) # 随便打一个
                    else: # 有一个能射击，则反击他
                        for oppBattler in oppBattlers:
                            if oppBattler.canShoot: # 找到能射击的敌人
                                actions = battler.try_dodge(oppBattler)
                                if len(actions) == 0: # 不能闪避
                                    if battler.canShoot:
                                        self.set_status(Status.READY_TO_FIGHT_BACK)
                                        return battler.shoot_to(oppBattler)
                                    else: # 要凉了 ...
                                        break
                                elif len(actions) == 1:
                                    action = self.try_make_decision(actions[0])
                                else:
                                    action = self.try_make_decision(actions[0],
                                                self.try_make_decision(actions[1]))
                                if Action.is_move(action): # 统一判断
                                    self.set_status(Status.READY_TO_DODGE)
                                    return action
                                # 没有办法？尝试反击
                                if battler.canShoot:
                                    self.set_status(Status.READY_TO_FIGHT_BACK)
                                    return battler.shoot_to(oppBattler)
                                else: # 要凉了
                                    break
                        # 没有办法对付 ..
                        self.set_status(Status.DYING)
                    # 无所谓的办法了...
                    return self.try_make_decision(battler.get_next_attack_action())

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
            status = assess_aggressive(battler, oppBattler)
            self.set_status(status)

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
                            self.set_status(Status.READY_TO_KILL_ENEMY)
                            return battler.shoot_to(oppBattler)
                    attackAction = battler.get_next_attack_action() # 其他情况，优先进攻，不与其纠缠
                    realAction = self.try_make_decision(attackAction) # 默认的进攻路线
                    if Action.is_stay(realAction): # 存在风险
                        if Action.is_move(attackAction):
                            # 原本移动或射击，因为安全风险而变成停留，这种情况可以尝试射击，充分利用回合数
                            # TODO:
                            #   实际上，很多时候最佳路线选择从中线进攻，但从两侧进攻也是等距离的，
                            #   在这种情况下，由于采用从中线的进攻路线，基地两侧的块并不落在线路上，因此会被
                            #   忽略，本回合会被浪费。但是进攻基地两侧的块往往可以减短路线。因此此处值得进行
                            #   特殊判断
                            fields = battler.get_destroyed_fields_if_shoot(attackAction)
                            route = battler.get_shortest_attacking_route()
                            for field in fields:
                                if is_block_in_route(field, route): # 为 block 对象，该回合可以射击
                                    action = self.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        self.set_status(Status.KEEP_ON_MARCHING)
                                        return action
                            # TODO: 此时开始判断是否为基地外墙，如果是，则射击
                            for field in fields:
                                if battler.check_is_outer_wall_of_enemy_base(field):
                                    action = self.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        self.set_status(Status.KEEP_ON_MARCHING)
                                        return action
                        # 其余情况照常
                        return realAction
                    # 否则不予理会，直接移动或者反击
                    action = self.try_make_decision(battler.get_next_attack_action())
                    if not Action.is_stay(action):
                        self.set_status(Status.KEEP_ON_MARCHING)
                        return action
                    action = self.try_make_decision(battler.shoot_to(oppBattler))
                    if Action.is_shoot(action):
                        self.set_status(Status.READY_TO_FIGHT_BACK)
                        return action
                else:
                    # 对方有炮弹，需要分情况 5ccb3ce1a51e681f0e8b4de1
                    #-----------------------------
                    # 1. 如果是侵略性的，则优先闪避，并且要尽量往和进攻路线方向一致的方向闪避，否则反击
                    # 2. 如果是僵持的，那么优先堵路，类似于 Defensive
                    #
                    if status == Status.STALEMENT:
                        # 首先把堵路的思路先做了，如果不能射击，那么同 aggressive
                        if battler.canShoot:
                            self.set_status(Status.READY_TO_BLOCK_ROAD)
                            return battler.shoot_to(oppBattler)

                    # 闪避，尝试找最佳方案
                    defenseAction = Action.STAY
                    if battler.canShoot:
                        defenseAction = battler.shoot_to(oppBattler)
                    actions = battler.try_dodge(oppTank)
                    attackAction = battler.get_next_attack_action()
                    for action in actions:
                        if Action.is_move(action) and Action.is_same_direction(action, attackAction):
                            realAction = self.try_make_decision(action) # 风险评估
                            if Action.is_move(realAction):
                                self.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                return realAction # 闪避加行军
                    # 没有最佳的闪避方案，仍然尝试闪避
                    if len(actions) == 0: # 采用后续方案
                        action = Action.STAY
                    elif len(actions) == 1:
                        action = self.try_make_decision(actions[0])
                    elif len(actions) == 2:
                        action = self.try_make_decision(actions[0],
                                    self.try_make_decision(actions[1]))
                    if Action.is_move(action): # 统一处理
                        self.set_status(Status.READY_TO_DODGE)
                        return action
                    # 不能闪避，只能还击
                    if Action.is_shoot(defenseAction):
                        self.set_status(Status.READY_TO_FIGHT_BACK)
                    else: # 没有炮弹，凉了 ...
                        self.set_status(Status.DYING)
                    return defenseAction

                # 所有其他的情况？
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
                            self.set_status(Status.READY_TO_KILL_ENEMY)
                            return battler.shoot_to(oppBattler)
                    #
                    # 不能马上打死，敌人又无法攻击
                    #-------------------------------
                    # 优先堵路，根据双方距离判断
                    #
                    _route = battler.get_route_to_enemy_by_movement(oppBattler)
                    routeLen = get_route_length(_route)
                    assert routeLen != INFINITY_ROUTE_LENGTH, "route not found ?" # 必定能找到路！
                    assert routeLen > 0, "unexpected overlapping enemy, or "
                    if routeLen == 1: # 双方相邻，选择等待
                        self.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY
                    elif routeLen > 2: # 和对方相隔两个格子以上
                        if self.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全逼近
                            action = battler.move_to(oppBattler)
                            self.set_status(Status.READY_TO_BLOCK_ROAD) # 可以认为在堵路 ...
                            return action
                        else:
                            self.set_status(Status.READY_TO_BLOCK_ROAD)
                            return Action.STAY # 否则只好等额爱
                    else: # routeLen == 2:
                        # 相距一个格子，可以前进也可以等待，均有风险
                        #----------------------------------------
                        # 1. 如果对方当前回合无法闪避，下一回合最多只能接近我
                        #    - 如果对方下回合可以闪避，那么我现在等待是意义不大的，不如直接冲上去和他重叠
                        #    - 如果对方下回合仍然不可以闪避，那么我就选择等待，反正它也走不了
                        # 2. 如果对方当前回合可以闪避，那么默认冲上去和他重叠
                        #    - 如果我方可以射击，那么对方应该会判定为闪避，向两旁走，那么我方就是在和他逼近
                        #    - 如果我方不能射击，对方可能会选择继续进攻，如果对方上前和我重叠，就可以拖延时间
                        if len( oppBattler.try_dodge(battler) ) == 0:
                            # 对手当前回合不可闪避，当然我方现在也不能射击。现在假设他下一步移向我
                            action = oppBattler.move_to(battler) # 对方移向我
                            if map_.is_valid_move_action(oppBattler, action):
                                map_.simulate_one_action(oppBattler, action) # 提交模拟
                                if len( oppBattler.try_dodge(battler) ) == 0:
                                    # 下回合仍然不可以闪避，说明可以堵路
                                    map_.revert()
                                    self.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                                map_.revert()
                                # 否则直接冲上去
                                if self.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全移动
                                    moveAction = battler.move_to(oppBattler)
                                    self.set_status(Status.READY_TO_BLOCK_ROAD) # 可以认为在堵路
                                    return moveAction
                                else: # 冲上去不安全，那就只能等到了
                                    self.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                        else:
                            # 对手当前回合可以闪避，那么尝试冲上去和他重叠
                            # TODO:
                            #   可能弄巧成拙 5cca97a4a51e681f0e8ad227
                            #
                            #   这个问题需要再根据情况具体判断！
                            #
                            '''
                            if self.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全重叠
                                moveAction = battler.move_to(oppBattler)
                                self.set_status(Status.READY_TO_BLOCK_ROAD)
                                return moveAction
                            else: # 有风险，考虑等待
                                self.set_status(Status.READY_TO_BLOCK_ROAD)
                                return Action.STAY
                            '''
                            #
                            # TODO:
                            #   是否应该根据战场情况进行判断，比如停下来堵路对方一定无法走通？
                            #
                            #   假设自己为钢墙然后搜索对方路径？
                            #
                            self.set_status(Status.READY_TO_BLOCK_ROAD)
                            return Action.STAY
                # 对方可以射击
                else:
                    if battler.canShoot: # 优先反击
                        self.set_status(Status.READY_TO_FIGHT_BACK)
                        return battler.shoot_to(oppBattler)
                    # 不能反击，只好闪避
                    actions = battler.try_dodge(oppBattler)
                    if len(actions) == 0:
                        self.set_status(Status.DYING) # 凉了 ...
                        action = Action.STAY
                    elif len(actions) == 1:
                        action = self.try_make_decision(actions[0])
                    else: # len(actions) == 2:
                        action = self.try_make_decision(actions[0],
                                        self.try_make_decision(actions[1]))
                    if Action.is_move(action): # 统一判断
                        self.set_status(Status.READY_TO_DODGE)
                        return action
                    # 否则就凉了 ...
                    self.set_status(Status.DYING)
                # 所有其他情况
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




        # (inserted) 准备破墙信号
        #--------------------------
        # 1. 先为自己找后路，确保自己开墙后可以闪避
        #
        if signal == Signal.PREPARE_FOR_BREAK_BRICK:
            self.set_status(Status.WAIT_FOR_MARCHING)      # 用于下回合触发
            self.set_status(Status.HAS_ENEMY_BEHIND_BRICK) # 用于下回合触发
            attackAction = battler.get_next_attack_action()
            oppTank = battler.get_enemy_behind_brick(attackAction)
            assert oppTank is not None
            dodgeActions = battler.try_dodge(oppTank)
            if len(dodgeActions) == 0:
                # 准备凿墙
                breakBrickActions = battler.break_brick_for_dodge(oppTank)
                if len(breakBrickActions) == 0: # 两边均不是土墙
                    return (  Action.STAY, Signal.CANHANDLED ) # 不能处理，只好等待
                else:
                    self.set_status(Status.READY_TO_PREPARE_FOR_BREAK_BRICK)
                    return ( breakBrickActions[0], Signal.READY_TO_PREPARE_FOR_BREAK_BRICK )
            else:
                # 可以闪避，那么回复团队一条消息，下一步是破墙动作
                shootAction = battler.shoot_to(oppTank)
                self.set_status(Status.READY_TO_BREAK_BRICK)
                return ( shootAction, Signal.READY_TO_BREAK_BRICK )


        # (inserted) 主动打破重叠的信号
        #------------------------------
        # 1. 如果是侵略模式，则主动前进/射击
        # 2. 如果是防御模式，则主动后退
        # 3. 如果是僵持模式？ 暂时用主动防御逻辑
        #       TODO:
        #           因为还没有写出强攻信号，主动攻击多半会失败 ...
        #
        if signal == Signal.PREPARE_FOR_BREAK_OVERLAP:
            self.set_status(Status.ENCOUNT_ENEMY)
            self.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)
            status = assess_aggressive(battler, oppBattler)
            self.set_status(status)
            # 先处理主动攻击逻辑
            if status == Status.AGGRESSIVE:
                action = battler.get_next_attack_action()
                if Action.is_shoot(action): # 能触发这个信号，保证能射击
                    self.set_status(Status.READY_TO_BREAK_OVERLAP)
                    self.set_status(Status.KEEP_ON_MARCHING)
                    return ( action, Signal.READY_TO_BREAK_OVERLAP )
                elif Action.is_move(action): # 专门为这个情况写安全性测试
                    if self.is_safe_to_break_overlap_by_movement(action, oppBattler):
                        # 没有风险，且已知这个移动是符合地图情况的
                        self.set_status(Status.READY_TO_BREAK_OVERLAP)
                        self.set_status(Status.KEEP_ON_MARCHING)
                        return ( action, Signal.READY_TO_BREAK_OVERLAP )
                    else:
                        self.set_status(Status.KEEP_ON_OVERLAPPING) # 继续保持状态
                        return ( Action.STAY, Signal.CANHANDLED )
                else: # 只能等待？ 注定不会到达这里
                    self.set_status(Status.KEEP_ON_OVERLAPPING) # 继续保持状态
                    return ( Action.STAY, Signal.CANHANDLED )
            elif status == Status.DEFENSIVE or status == Status.STALEMENT:
                oppAction = oppBattler.get_next_attack_action() # 模拟对方的侵略性算法
                if Action.is_move(oppAction) or Action.is_shoot(oppAction): # 大概率是移动
                    # 主要是为了确定方向
                    oppAction %= 4
                    if self.is_safe_to_break_overlap_by_movement(oppAction, oppBattler):
                        self.set_status(Status.READY_TO_BREAK_OVERLAP)
                        self.set_status(Status.READY_TO_BLOCK_ROAD)
                        return ( oppAction, Signal.READY_TO_BREAK_OVERLAP )
                    else:
                        # 否则就等待？
                        # TODO:
                        #   是否检查实际？推测决策
                        self.set_status(Status.KEEP_ON_OVERLAPPING)
                        return ( Action.STAY, Signal.CANHANDLED )
                else: # 不可能这种情况？
                    pass
            #else: # 僵持模式 -> 暂时归入主动防御
            #    pass




        # 与敌人重合时，一般只与一架坦克重叠
        #--------------------------
        # 1. 根据路线评估侵略性，确定采用进攻策略还是防守策略
        # 2.
        #
        if battler.has_overlapping_enemy():
            self.set_status(Status.ENCOUNT_ENEMY)
            self.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)

            # 评估进攻路线长度，以确定采用保守策略还是入侵策略
            status = assess_aggressive(battler, oppBattler)
            self.set_status(status)

            # 侵略模式
            #-----------
            # 1. 直奔对方基地，有机会就甩掉敌人。
            if status == Status.AGGRESSIVE:
                if not oppBattler.canShoot: # 对方不能射击，对自己没有风险
                    # 尝试继续行军
                    action = battler.get_next_attack_action()
                    if Action.is_move(action): # 下一步预计移动
                        realAction = self.try_make_decision(action)
                        if Action.is_move(realAction): # 继续起那就
                            self.set_status(Status.KEEP_ON_MARCHING)
                            return realAction
                        # 否则就是等待了，打得更有侵略性一点，可以尝试向同方向开炮！
                        realAction = self.try_make_decision(action + 4)
                        if Action.is_shoot(realAction):
                            self.set_status(Status.KEEP_ON_MARCHING)
                            return realAction
                    elif Action.is_shoot(action): # 下一步预计射击
                        realAction = self.try_make_decision(action)
                        if Action.is_shoot(realAction):
                            self.set_status(Status.KEEP_ON_MARCHING)
                            return realAction
                    else: # 否则停留
                        self.set_status(Status.KEEP_ON_OVERLAPPING) # 可能触发 Signal.PREPARE_FOR_BREAK_OVERLAP
                        return Action.STAY
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
                    if Action.is_move(oppAction): # 大概率是移动
                        # TODO:
                        #   回头堵路并不一定是最好的办法因为对于无脑 bot
                        #   没有办法射击就前进，如果我恰好后退，就相当于对方回退了一步
                        #   这种情况下应该考虑回头开炮！
                        #
                        if self.is_safe_to_break_overlap_by_movement(oppAction): # 模仿敌人的移动方向
                            self.set_status(Status.READY_TO_BLOCK_ROAD) # 认为在堵路
                            return oppAction
                # 否则等待
                self.set_status(Status.READY_TO_BLOCK_ROAD)
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



        # 先处理团队信号
        # -------------
        #


        #
        # 先观察敌方状态，确定应该进攻。
        # 尽管对于大部分地图来讲，遵寻 BFS 的搜索路线，可以最快速地拆掉对方基地
        # 但是对于一些地图来说，由于地形限制，我方拆家速度注定快不过对方，
        # 这种时候就需要调整为防御策略
        #
        oppTank = battler.get_nearest_enemy() # 从路线距离分析确定最近敌人
        oppBattler = BattleTank(oppTank)
        status = assess_aggressive(battler, oppBattler)
        self.set_status(status)

        # 主动防御策略
        #---------------------
        # TODO:
        #   主动堵路或预判射击，该如何权衡？
        #-------------------------------------
        # 1. 主动追击敌方目标，并会预判对方下回合行为进行射击
        # 2. 主动堵路，和敌方目标重叠，这种情况对应于两者斜对角的情况
        # 3. TODO:
        #       尽可能少拆自己基地的外墙 ...
        #
        if status == Status.DEFENSIVE: # 防御性的，就触发主动防御
            #
            #   前期如果过早决策为 Defensive 可能会错失战机，因为并不是每个人都会使用相同
            #   的 BFS 算法，如果一开始就把对方界定为和己方的算法一致，那么可能会显得过于消极
            #   因此可以考虑前几个回合忽略这个状态，而改用常规进攻，一定步数后，再决策是否为
            #   Defensive
            #
            currentTurn = map_.turn # 这个值表示决策前为第几回合，初值为第 0 回合
            if currentTurn < MINIMAL_TURNS_FOR_ACTIVE_DEFENSIVE_DECISION:
                # 相当于 右边值 所代表的的回合数结束，下一回合开始开启主动防御
                self.remove_status(Status.DEFENSIVE)
                self.remove_status(Status.STALEMENT)
                self.set_status(Status.AGGRESSIVE) # 前期以侵略性为主

            else:
                #
                # 先处理特殊情况
                # ---------------------
                # 在敌人就要攻击我方基地的情况下，应该优先移动，而非预判击杀
                # 这种防御性可能会带有自杀性质
                #
                # TODO:
                # 1. 如果敌人当前回合炮弹冷却，下一炮就要射向基地，如果我方坦克下一步可以拦截
                #    那么优先移动拦截，而非防御
                # 2. 如果敌人当前回合马上可以开盘，那么仍然考虑拦截（自杀性）拦截，可以拖延时间
                #    如果此时另一个队友还有两步就拆完了，那么我方就有机会胜利
                #
                if oppBattler.is_face_to_enemy_base(): # 面向基地
                    if oppBattler.canShoot: # 敌方可以射击，我方如果一步内可以拦截，则自杀性防御
                        for action in Action.MOVE_ACTIONS: # 尝试所有可能的移动情况
                            if map_.is_valid_move_action(tank, action):
                                map_.simulate_one_action(tank, action)
                                if not oppBattler.is_face_to_enemy_base(): # 此时不再面向我方基地，为正确路线
                                    map_.revert()
                                    self.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                    return action
                                map_.revert()
                    else: # 敌方不可射击
                        for action in Action.MOVE_ACTIONS: # 敌方不能射击，我方尝试移动两步
                            if map_.is_valid_move_action(tank, action):
                                map_.simulate_one_action(tank, action)
                                if not oppBattler.is_face_to_enemy_base(): # 一步防御成功
                                    map_.revert()
                                    self.set_status(Status.BLOCK_ROAD_FOR_OUR_BASE)
                                    return action
                                else: # 尝试第二步
                                    if map_.is_valid_move_action(tank, action):
                                        map_.simulate_one_action(tank, action)
                                        if not oppBattler.is_face_to_enemy_base(): # 两步防御成功
                                            map_.revert()
                                            map_.revert() # 回滚两个回合
                                            self.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                            return action # 当前回合先移动一步，下回合则在此处按一步判定
                                        map_.revert()
                                map_.revert()
                    # 没有救了 ... 那就预判射击把，万一敌方 tank 的策略有误，恰好被杀 ...

                enemyAction = oppBattler.get_next_attack_action()
                self.set_status(Status.HUNTING_ENEMY)
                #
                # TODO:
                #   还可以堵路，怎么设计？
                #   可以通过记忆来判断 5cca6810a51e681f0e8ab0c8 ?
                #
                #   主动预判，可能会弄巧成拙 5cca97a4a51e681f0e8ad227
                #
                #
                # 预判是否可以射击
                # --------------------
                #   假设敌方采用与我相同的 BFS 算法，那么他下一回合的移动路线会是什么,
                #   如果是移动行为，那么判断移动后是否可能恰好处在我方坦克的范围内，
                #   在这种情况下，有可能将敌方坦克击杀
                #
                # TODO:
                # 1. 可以根据历史行为拟合出路线，猜测下一回合敌方的移动位置？
                # 2. 可以评估敌方的侵略性，如果能够从一些动作中学习到的话。那么这一步可以预测
                #    击杀的概率，从而决定是击杀还是继续

                #
                # 应该优先堵路？因为对方显然不想和你对抗？
                #

                if Action.is_move(enemyAction):
                    if battler.canShoot: # 如果我方能射击，判断是否能击杀，必须在地图模拟前先行判断
                        map_.simulate_one_action(oppTank, enemyAction) # 提交地图模拟
                        for _enemy in oppBattler.get_enemies_around():
                            if _enemy is tank: # 发现敌方 tank 下一步决策后，会出现在我方 tank 前
                                shootAction = battler.shoot_to(oppTank) # 保存这个动作
                                map_.revert()
                                self.set_status(Status.ANTICIPATE_TO_KILL_ENEMY)
                                # 侵略行为，不需要检查安全性，否则大概率检查不通过 ...
                                return shootAction
                        map_.revert()
                elif Action.is_shoot(enemyAction): # 射击行为，遇到墙了？
                    pass

                # 否则正常追击
                huntingAction = battler.get_next_hunting_action(oppTank)
                return self.try_make_decision(huntingAction)


        # 如果是僵持，那么主动进攻？
        elif status == Status.STALEMENT:
            pass


        #　侵略性的，那么主动进攻
        else:
            pass



        #///////////#
        #  常规进攻  #
        #///////////#


        # (inserted) 准备破墙信号
        #--------------------------
        # 1. 先为自己找后路，确保自己开墙后可以闪避
        #
        if signal == Signal.PREPARE_FOR_BREAK_BRICK:
            self.set_status(Status.WAIT_FOR_MARCHING)      # 用于下回合触发
            self.set_status(Status.HAS_ENEMY_BEHIND_BRICK) # 用于下回合触发
            attackAction = battler.get_next_attack_action()
            oppTank = battler.get_enemy_behind_brick(attackAction)
            assert oppTank is not None
            dodgeActions = battler.try_dodge(oppTank)
            if len(dodgeActions) == 0:
                # 准备凿墙
                breakBrickActions = battler.break_brick_for_dodge(oppTank)
                if len(breakBrickActions) == 0: # 两边均不是土墙
                    return (  Action.STAY, Signal.CANHANDLED ) # 不能处理，只好等待
                else:
                    self.set_status(Status.READY_TO_PREPARE_FOR_BREAK_BRICK)
                    return ( breakBrickActions[0], Signal.READY_TO_PREPARE_FOR_BREAK_BRICK )
            else:
                # 可以闪避，那么回复团队一条消息，下一步是破墙动作
                shootAction = battler.shoot_to(oppTank)
                self.set_status(Status.READY_TO_BREAK_BRICK)
                return ( shootAction, Signal.READY_TO_BREAK_BRICK )


        # 没有遭遇任何敌人
        #-----------------
        # 1. 进攻
        # 2. 如果存在安全风险，尝试采用射击代替移动
        #
        attackAction = battler.get_next_attack_action()
        realAction = self.try_make_decision(attackAction)
        if Action.is_stay(realAction): # 存在风险
            if Action.is_move(attackAction):
                # 原本的移动，现在变为停留，则尝试射击
                fields = battler.get_destroyed_fields_if_shoot(attackAction)
                route = battler.get_shortest_attacking_route()
                for field in fields:
                    if is_block_in_route(field, route): # 为 block 对象，该回合可以射击
                        action = self.try_make_decision(battler.shoot_to(field))
                        if Action.is_shoot(action):
                            self.set_status(Status.KEEP_ON_MARCHING)
                            return action
                # 再检查是否为基地外墙
                for field in fields:
                    if battler.check_is_outer_wall_of_enemy_base(field):
                        action = self.try_make_decision(battler.shoot_to(field))
                        if Action.is_shoot(action):
                            self.set_status(Status.KEEP_ON_MARCHING)
                            return action

            elif Action.is_shoot(attackAction):
                # 如果为射击行为，检查是否是墙后敌人造成的
                if battler.has_enemy_behind_brick(attackAction):
                    self.set_status(Status.HAS_ENEMY_BEHIND_BRICK)

            # 否则停止不前
            self.set_status(Status.WAIT_FOR_MARCHING) # 可能触发 Signal.PREPARE_FOR_BREAK_BRICK
            self.set_status(Status.PREVENT_BEING_KILLED) # TODO: 这个状态是普适性的，希望到处都能补全
            return Action.STAY
        # 否则继续攻击
        self.set_status(Status.KEEP_ON_MARCHING)
        return realAction

#{ END }#
