# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 00:35:10
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-09 07:11:21
"""
游戏玩家，操作着一架坦克，充当单人决策者

"""

__all__ = [

    "Tank2Player",

    ]

from .const import DEBUG_MODE
from .utils import outer_label, debug_print, debug_pprint
from .action import Action
from .field import BrickField, WaterField, EmptyField, TankField, BaseField
from .tank import BattleTank
from .strategy.signal import Signal
from .strategy.status import Status
from .strategy.search import get_searching_directions
from .strategy.estimate import assess_aggressive, MINIMAL_TURNS_FOR_ACTIVE_DEFENSIVE_DECISION



#{ BEGIN }#

class Player(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
        raise NotImplementedError


class Tank2Player(Player):

    _instances = {} # { (side, id): instance }

    def __new__(cls, tank, map=None, **kwargs):
        """
        以 (side, id) 为主键，缓存已经创建过的玩家类，使之为 Singleton

        Input:
            - tank   TankField/BattleTank   第一次必须是 TankField ，之后随意
            - map    Tank2Map
        """
        key = (tank.side, tank.id) # 只要有这两个属性就可以
        obj = __class__._instances.get(key)
        if obj is None:
            map_ = map
            if map_ is None:
                raise ValueError("map is required at first initialization")
            if not isinstance(tank, TankField):
                raise TypeError("tank must be a TankField object at first initialization")
            obj = object.__new__(cls, **kwargs)
            __class__._instances[key] = obj
            obj._initialize(tank, map_) # 使用自定义初始化条件初始化
        return obj

    def __init__(self, tank, map=None):
        pass

    def _initialize(self, tank, map):
        self._tank = tank
        self._map = map
        self._battler = BattleTank(tank, map)
        self._team = None       # Tank2Team
        self._teammate = None   # Tank2Player
        self._opponents = None  # [Tank2Player]
        self._status = set()    #　当前的状态，可以有多个
        self._riskyEnemy = None # 缓存引起潜在风险的敌人 BattleTank

    def __eq__(self, other):
        return self.side == other.side and self.id == other.id

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

    def remove_status(self, *status):
        """
        删除状态
        """
        for _status in status:
            self._status.discard(_status) # remove_if_exists

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

    def has_status_in_previous_turns(self, status, turns=1, player=None):
        """
        非常丑陋的设计
        --------------
        本来决定只让 team 来管理团队记忆，但是后来发现有些需要靠记忆进行决策的单人行为
        也要通过团队通过信号进行触发，这实在是太麻烦、低效、且不直截了。玩家也应该拥有记忆。
        因此这里就把 team 的一个关键的状态记忆查找函数代理到这里，用于玩家查找自己的记忆。

        但是这就导致设计上存在了上下互相依赖的糟糕设计，也就是 player 作为 team 的组成
        他竟然代理了 team 的函数。

        这一定程度上反映了这个架构仍然是存在很多设计不周的地方的

        (2019.05.07)

        """
        if player is None: # 与 team 的函数不同，此处默认 player 为 self
            player = self  # 如果需要设定为敌人，那么需要特别指定，不过可能是违背设计原则的行为
        return self._team.has_status_in_previous_turns(player, status, turns=turns)

    def get_previous_action(self, back=1, player=None):
        """
        同上
        """
        if player is None:
            player = self
        return self._team.get_previous_action(player, back)

    def get_risky_enemy_battler(self):
        """
        引起预期行为被拒的敌人，因为该敌人有可能在我方采用预期行为的下一回合将我方击杀
        """
        return self._riskyEnemy # -> BattleTank

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
                        self._riskyEnemy = oppBattler
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
                            actions = battler.try_dodge(oppBattler)
                            if len(actions) == 0: # 无法回避，危险行为
                                map_.revert()
                                map_.revert() # 再回退外层模拟
                                self._riskyEnemy = oppBattler
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
                        self._riskyEnemy = _oppBattler
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
                    self._riskyEnemy = _oppBattler
                    return False
            map_.revert()
        else:
            return True # 否则是安全的

    def is_suitable_to_overlap_with_enemy(self, oppBattler):
        """
        当两者均没有炮弹，然后中间相差一格时，冲上去和敌方坦克重叠是否合适？

        WARNING:
        ------------
        1. 该函数仅适用于两者间移动路劲长度为 2 的情况，其他情况不适用

        2. 该函数判定为 False 的情况，表示适合堵路，不适合重叠，但是判定为
           False 并不表示一定要冲上去重叠，而是要根据当时的具体情况来判断

        """
        tank = self._tank
        map_ = self._map
        battler = self._battler

        _route = battler.get_route_to_enemy_by_movement(oppBattler)
        assert _route.length == 2

        action = oppBattler.move_to(battler)
        if map_.is_valid_move_action(oppBattler, action):
            #
            # 检查自己所处的位置是否是敌人必经之路
            # 如果是，那么就堵路
            #
            originRoute = oppBattler.get_shortest_attacking_route()
            blockingRoute = oppBattler.get_shortest_attacking_route( # 将我方坦克设为 Steel
                                    ignore_enemies=False, bypass_enemies=True)

            if originRoute.is_not_found(): # 不大可能，但是检查一下
                return False

            if blockingRoute.is_not_found(): # 直接就走不通了，当然非常好啦
                return False

            if blockingRoute.length - originRoute.length > 1: # 认为需要多打破一个以上土墙的情况叫做原路
                return False

        return True


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
        make_decision 的装饰
        ----------------------

        - 清除所有旧有状态
        - 清除可能的风险敌人
        - 统一处理回复格式

        WARNING:
            - 申明为 make_decision 过程中的缓存变量，必须在下一次决策前率先清楚

        """
        self.clear_status()     # 先清除所有的状态
        self._riskyEnemy = None # 清楚所有缓存的风险敌人

        res = self._make_decision(signal)

        if isinstance(res, (tuple, list)) and len(res) == 2:
            outputSignal = res[1]
            action = res[0]
        else:
            outputSignal = Signal.NONE
            action = res

        inputSignal = signal

        if inputSignal != Signal.NONE and outputSignal == Signal.NONE:
            outputSignal = Signal.UNHANDLED # 没有回复团队信号，事实上不允许这样，至少是 CANHANDLED

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
            self.set_status(Status.RELOADING)

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
                                if route.has_block(field): # 为 block 对象，该回合可以射击
                                    action = self.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        self.set_status(Status.PREVENT_BEING_KILLED)
                                        self.set_status(Status.KEEP_ON_MARCHING)
                                        return action
                            # TODO: 此时开始判断是否为基地外墙，如果是，则射击
                            for field in fields:
                                if battler.check_is_outer_wall_of_enemy_base(field):
                                    action = self.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        self.set_status(Status.PREVENT_BEING_KILLED)
                                        self.set_status(Status.KEEP_ON_MARCHING)
                                        return action

                        # 刚刚对射为两回合，尝试打破对射僵局
                        #--------------------------------
                        # 1. 当前为侵略性的，尝试回退一步，与对方重叠
                        #
                        # TODO:
                        #   尝试了两回合想想还是算了吧 ... 感觉就是在放对面过来 5cd10315a51e681f0e900fa8
                        '''
                        if self.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=3):
                            backMoveAction = battler.back_away_from(oppBattler) # 尝试背离敌人
                            action = self.try_make_decision(backMoveAction)
                            if Action.is_move(action):
                                self.set_status(Status.READY_TO_BACK_AWAY)
                                return action
                        '''

                        # 如果之前是对射，在这里需要延续一下对射状态
                        if (self.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=1) # 上回合正在和对方对射
                            and not battler.canShoot    # 但是我方本回合不能射击
                            and not oppBattler.canShoot # 并且对方本回合不能射击
                            ):
                            self.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射状态，用于后方打破僵持

                        # 其余情况照常
                        self.set_status(Status.PREVENT_BEING_KILLED)
                        return realAction
                    # 否则不予理会，直接移动或者反击
                    action = self.try_make_decision(battler.get_next_attack_action())
                    if not Action.is_stay(action):
                        # 补丁
                        #----------------------------
                        # 针对两者距离为 2 的情况，不能一概而论！
                        #
                        if status == Status.STALEMENT: # 僵持模式考虑堵路
                            _route = battler.get_route_to_enemy_by_movement(oppBattler)
                            assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                            assert _route.length > 0, "unexpected overlapping enemy"
                            if _route.length == 2:
                                if not self.is_suitable_to_overlap_with_enemy(oppBattler): # 更适合堵路
                                    self.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                        # 其他情况均可以正常移动
                        self.set_status(Status.KEEP_ON_MARCHING)
                        return action
                    #  不能移动，只好反击
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
                    # TODO:
                    #   可能需要团队信号协调 5ccc30f7a51e681f0e8c1668
                    #
                    if status == Status.STALEMENT:
                        # 首先把堵路的思路先做了，如果不能射击，那么同 aggressive
                        # TODO:
                        #   有的时候这并不是堵路，而是在拖时间！ 5ccf84eca51e681f0e8ede59

                        # 上一回合保持重叠，但是却被敌人先过了，这种时候不宜僵持，应该直接走人
                        # 这种情况下直接转为侵略模式！
                        if (self.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                            and (self.has_status_in_previous_turns(Status.READY_TO_BLOCK_ROAD, turns=1)
                                or self.has_status_in_previous_turns(Status.KEEP_ON_OVERLAPPING, turns=1))
                            ):
                            pass # 直接过到侵略模式
                        else: # 否则算作正常的防守
                            if battler.canShoot:
                                self.set_status(Status.READY_TO_BLOCK_ROAD, Status.READY_TO_FIGHT_BACK)
                                if battler.get_manhattan_distance_to(oppBattler) == 1:
                                    self.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射
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
                            realAction = self.try_make_decision(action) # 风险评估
                            if Action.is_move(realAction):
                                self.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                return realAction # 闪避加行军

                    # 没有最佳的闪避方案，仍然尝试闪避
                    #-----------------------------
                    # 但是不能向着增加攻击线路长短的方向闪避！
                    #
                    currentRoute = battler.get_shortest_attacking_route()
                    for action in actions:
                        if Action.is_move(action):
                            realAction = self.try_make_decision(action)
                            if Action.is_move(realAction):
                                map_.simulate_one_action(battler, action)
                                route = battler.get_shortest_attacking_route()
                                map_.revert()
                                if route.length > currentRoute.length: # 不能超过当前路线长度，否则就是浪费一回合
                                    continue
                                else:
                                    self.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                    return realAction

                    # 没有不能不导致路线编程的办法，如果有炮弹，那么优先射击！
                    # 5ccef443a51e681f0e8e64d8
                    #-----------------------------------
                    if Action.is_shoot(defenseAction):
                        self.set_status(Status.READY_TO_FIGHT_BACK)
                        if battler.get_manhattan_distance_to(oppBattler) == 1:
                            self.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY)
                        return defenseAction

                    # 如果不能射击，那么终究还是要闪避的
                    # 或者是无法后方移动，为了打破僵局，尝试闪避
                    #----------------------------------
                    for action in actions:
                        if Action.is_move(action):
                            realAction = self.try_make_decision(action)
                            if Action.is_move(realAction):
                                self.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                #
                                # 因为这种情况很有可能会出现死循环 5cd009e0a51e681f0e8f3ffb
                                # 为了后续能够打破这种情况，这里额外添加一个状态进行标记
                                #
                                self.set_status(Status.WILL_DODGE_TO_LONG_WAY)
                                return realAction

                    self.set_status(Status.DYING) # 否则就凉了 ...
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
                            self.set_status(Status.READY_TO_KILL_ENEMY)
                            return battler.shoot_to(oppBattler)
                    #
                    # 不能马上打死，敌人又无法攻击
                    #-------------------------------
                    # 优先堵路，根据双方距离判断
                    #
                    _route = battler.get_route_to_enemy_by_movement(oppBattler)
                    assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                    assert _route.length > 0, "unexpected overlapping enemy"

                    if _route.length == 1: # 双方相邻，选择等待

                        # 此处首先延续一下对射状态
                        if (self.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=1) # 上回合正在和对方对射
                            and not battler.canShoot    # 但是我方本回合不能射击
                            and not oppBattler.canShoot # 并且对方本回合不能射击
                            ):
                            self.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射状态，用于后方打破僵持

                        self.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY
                    elif _route.length > 2: # 和对方相隔两个格子以上
                        if self.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全逼近
                            action = battler.move_to(oppBattler)
                            self.set_status(Status.READY_TO_BLOCK_ROAD) # 可以认为在堵路 ...
                            return action
                        else:
                            self.set_status(Status.READY_TO_BLOCK_ROAD)
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
                            return Action.STAY"""
                        self.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY # 似乎没有比这个这个更好的策略 ...
                # 对方可以射击
                else:
                    if battler.canShoot: # 优先反击
                        self.set_status(Status.READY_TO_FIGHT_BACK)
                        if battler.get_manhattan_distance_to(oppBattler) == 1:   # 贴脸
                            self.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 触发对射状态
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



        # (inserted) 主动打破重叠的信号
        #------------------------------
        # 1. 如果是侵略模式，则主动前进/射击
        # 2. 如果是防御模式，则主动后退
        # 3. 如果是僵持模式？ 暂时用主动防御逻辑
        #       TODO:
        #           因为还没有写出强攻信号，主动攻击多半会失败 ...
        #
        if signal == Signal.SUGGEST_TO_BREAK_OVERLAP:
            self.set_status(Status.ENCOUNT_ENEMY)
            self.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)
            status = assess_aggressive(battler, oppBattler)
            self.set_status(status)
            if status != Status.DEFENSIVE:
                #
                # 非防御状态，往前走
                #
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
            else:
                #　防御状态，往后退堵路
                #------------------------
                # 为了防止这种情况的发生 5cd356e5a51e681f0e921453
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
                        if self.is_safe_to_break_overlap_by_movement(oppAction, oppBattler):
                            self.set_status(Status.READY_TO_BREAK_OVERLAP)
                            self.set_status(Status.READY_TO_BLOCK_ROAD)
                            return ( oppAction, Signal.READY_TO_BREAK_OVERLAP )

                else: # 否则选择等待
                    self.set_status(Status.KEEP_ON_OVERLAPPING)
                    return ( Action.STAY, Signal.CANHANDLED )



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
            # 1. 直奔对方基地，有机会就甩掉敌人
            #
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
                        self.set_status(Status.KEEP_ON_OVERLAPPING) # 可能触发 Signal.SUGGEST_TO_BREAK_OVERLAP
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
                        if self.is_safe_to_break_overlap_by_movement(oppAction, oppBattler): # 模仿敌人的移动方向
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




        #
        # 先观察敌方状态，确定应该进攻。
        # 尽管对于大部分地图来讲，遵寻 BFS 的搜索路线，可以最快速地拆掉对方基地
        # 但是对于一些地图来说，由于地形限制，我方拆家速度注定快不过对方，
        # 这种时候就需要调整为防御策略


        #
        # 现在没有和敌人正面相遇
        # 在进入主动防御和行军之前，首先先处理一种特殊情况
        # 这种特殊情况不应该依赖于任意一种模式，也要求坦克一定要
        # 和他有关系，否则很有可能被别人隔墙牵制
        # ----------------------------------------------
        # 在敌人就要攻击我方基地的情况下，应该优先移动，而非预判击杀
        # 这种防御性可能会带有自杀性质
        #
        # TODO:
        # 1. 如果敌人当前回合炮弹冷却，下一炮就要射向基地，如果我方坦克下一步可以拦截
        #    那么优先移动拦截，而非防御
        # 2. 如果敌人当前回合马上可以开盘，那么仍然考虑拦截（自杀性）拦截，可以拖延时间
        #    如果此时另一个队友还有两步就拆完了，那么我方就有机会胜利
        #
        for oppBattler in [ player.battler for player in self._opponents ]:
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


        oppTank = battler.get_nearest_enemy() # 从路线距离分析确定最近敌人
        oppBattler = BattleTank(oppTank)
        status = assess_aggressive(battler, oppBattler)
        self.set_status(status)


        # 暂时禁用主动防御！目前开发得太不完善了，容易反而延误战机

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
        """
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
        """


        # 重写主动防御策略
        #-----------------------
        # 不要追击敌人，而是选择保守堵路策略！
        #
        # 1. 对于路线差为 2 的情况，选择堵路，而非重叠
        # 2. 如果自己正常行军将会射击，那么判断射击所摧毁的块是否为敌人进攻路线上的块
        #    如果是，则改为己方改为移动或者停止
        #
        if status == Status.DEFENSIVE:
            #
            # 避免过早进入 DEFENSIVE 状态
            #
            currentTurn = map_.turn # 这个值表示决策前为第几回合，初值为第 0 回合
            if currentTurn < MINIMAL_TURNS_FOR_ACTIVE_DEFENSIVE_DECISION:
                # 相当于 右边值 所代表的的回合数结束，下一回合开始开启主动防御
                self.remove_status(Status.DEFENSIVE)
                self.set_status(Status.AGGRESSIVE)   # 前期以侵略性为主
            #
            # 判断路线是否为 2
            #-------------------
            # 如果是路线为 2
            # 则选择不重叠，只堵路
            #
            _route = battler.get_route_to_enemy_by_movement(oppBattler)
            assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
            assert _route.length > 0, "unexpected overlapping enemy"
            if _route.length == 2:
                if (
                        # 可能是主动防御但是为了防止重叠而等待
                        (
                            self.has_status_in_previous_turns(Status.ACTIVE_DEFENSIVE, turns=1)
                            and self.has_status_in_previous_turns(Status.READY_TO_BLOCK_ROAD, turns=1)
                            and Action.is_stay(self.get_previous_action(back=1))
                        )

                    or
                        # 可能是为了防止被杀而停止
                        (
                            self.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED)
                            and Action.is_stay(self.get_previous_action(back=1))
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
                            map_.simulate_one_action(oppBattler, enemyMoveAction)
                            for enemyDodgeAction in oppBattler.try_dodge(battler): # 如果敌人上前后可以闪避我
                                route1 = oppBattler.get_shortest_attacking_route()
                                map_.simulate_one_action(oppBattler, enemyDodgeAction)
                                route2 = oppBattler.get_shortest_attacking_route()
                                if route2.length <= route1.length: #　并且闪避的路线不是原路返回
                                    _shouldMove = True
                                map_.revert()
                                if _shouldMove:
                                    break
                            map_.revert()

                        #
                        # 真正的值得堵路的情况
                        #
                        if _shouldMove:
                            x1, y1 = battler.xy
                            x2, y2 = _route[1].xy # 跳过开头
                            moveAction = Action.get_move_action(x1, y1, x2, y2)
                            if map_.is_valid_move_action(battler, moveAction): # 稍微检查一下，应该本来是不会有错的
                                self.set_status(Status.ACTIVE_DEFENSIVE)
                                self.set_status(Status.READY_TO_BLOCK_ROAD)
                                return moveAction

                #
                # 否则选择不要上前和敌人重叠，而是堵路
                #
                self.set_status(Status.ACTIVE_DEFENSIVE)
                self.set_status(Status.READY_TO_BLOCK_ROAD)
                return Action.STAY

            #
            # 判断下一步是否可以出现在敌人的攻击路径之上 5cd31d84a51e681f0e91ca2c
            #-------------------------------
            # 如果可以，就移动过去
            #
            enemyAttackRoute = oppBattler.get_shortest_attacking_route()
            x1, y1 = battler.xy
            for x3, y3 in battler.get_surrounding_empty_field_points():
                if (x3, y3) in enemyAttackRoute:
                    moveAction = Action.get_move_action(x1, y1, x3, y3)
                    assert map_.is_valid_move_action(battler, moveAction)
                    willMove = False # 是否符合移动的条件
                    realAction = self.try_make_decision(moveAction)
                    if Action.is_move(realAction):
                        willMove = True
                    elif self.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1): # 打破僵局
                        oppPlayer = Tank2Player(self._riskyEnemy)
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
                        map_.simulate_one_action(battler, moveAction)
                        distance2 = battler.get_manhattan_distance_to(oppBattler)
                        if distance2 > distance1: # 向着远处移动了
                            pass
                        else:
                            map_.revert()
                            self.set_status(Status.ACTIVE_DEFENSIVE)
                            self.set_status(Status.READY_TO_BLOCK_ROAD)
                            return moveAction
                        map_.revert()


            #
            # 判断自己的下一步是否为敌人开路
            #-------------------------
            # 如果自己下一个行为是射击，然后所射掉的块为敌人进攻路线上的块
            # 那么将这个动作转为移动或者停止
            #
            attackAction = battler.get_next_attack_action()
            realAction = self.try_make_decision(attackAction)
            if Action.is_shoot(realAction):
                fields = battler.get_destroyed_fields_if_shoot(realAction)
                if len(fields) == 1:
                    field = fields[0]
                    if isinstance(field, BrickField):
                        enemyAttackRoute = oppBattler.get_shortest_attacking_route()
                        if enemyAttackRoute.has_block(field): # 打掉的 Brick 在敌人进攻路线上
                            self.set_status(Status.ACTIVE_DEFENSIVE)
                            moveAction = realAction - 4
                            return self.try_make_decision(moveAction) # 移动/停止


        #///////////#
        #  常规进攻  #
        #///////////#


        # (inserted) 准备破墙信号
        #--------------------------
        # 触发条件：
        #
        #   1. 对应于双方对峙，我方开好后路后触发某些条件强制破墙
        #   2. 对方刚刚从墙后移开，我方存在后路，这个时候强制破墙
        #
        # 收到这个信号的时候，首先检查是否可以闪避
        #
        #   1. 如果可以闪避，就返回可以破墙的信号
        #   2. 如果不可以闪避，就返回这回合准备后路的信号
        #
        if signal == Signal.PREPARE_FOR_BREAK_BRICK:
            self.set_status(Status.WAIT_FOR_MARCHING)      # 用于下回合触发
            self.set_status(Status.HAS_ENEMY_BEHIND_BRICK) # 用于下回合触发
            attackAction = battler.get_next_attack_action()
            oppTank = battler.get_enemy_behind_brick(attackAction, interval=-1)

            _undoRevertTurns = 0
            while oppTank is None: #　对应于敌方刚离开的那种触发条件
                # 可能存在多轮回滚，因为别人的策略和我们的不一样！
                # 给别人回滚的时候必须要考虑多回合！
                map_.revert()
                _undoRevertTurns += 1
                oppTank = battler.get_enemy_behind_brick(attackAction, interval=-1)

            self._riskyEnemy = BattleTank(oppTank) # 重新设置这个敌人！
            assert oppTank is not None
            dodgeActions = battler.try_dodge(oppTank)
            if len(dodgeActions) == 0:
                # 准备凿墙
                breakBrickActions = battler.break_brick_for_dodge(oppTank)
                if len(breakBrickActions) == 0: # 两边均不是土墙
                    res = (  Action.STAY, Signal.CANHANDLED ) # 不能处理，只好等待
                else:
                    self.set_status(Status.READY_TO_PREPARE_FOR_BREAK_BRICK)
                    res = ( breakBrickActions[0], Signal.READY_TO_PREPARE_FOR_BREAK_BRICK )
            else:
                # 可以闪避，那么回复团队一条消息，下一步是破墙动作
                shootAction = battler.shoot_to(oppTank)
                self.set_status(Status.READY_TO_BREAK_BRICK)
                res = ( shootAction, Signal.READY_TO_BREAK_BRICK )

            for _ in range(_undoRevertTurns):
                map_.undo_revert()

            return res

        # (inserted) 强攻信号
        #-------------------------
        if signal == Signal.FORCED_MARCH:
            attackAction = battler.get_next_attack_action() # 应该是移动行为，且不需检查安全性
            self.set_status(Status.READY_TO_FORCED_MARCH)
            return ( attackAction, Signal.READY_TO_FORCED_MARCH )


        # 没有遭遇任何敌人
        #-----------------
        # 1. 进攻
        # 2. 不会主动破墙
        # 3. 遇到僵局，会在指定回合后自动打破僵局
        # 4. 遇到有风险的路径导致需要停止不前的，会考虑寻找相同长度但是安全的路径，并改变方向
        #
        returnAction = Action.STAY # 将会返回的行为，默认为 STAY
        with outer_label() as OUTER_BREAK:
            for route in battler.get_all_shortest_attacking_routes(): # 目的是找到一个不是停留的动作，避免浪费时间

                # 首先清除可能出现的状态，也就是导致 stay 的状况
                self.remove_status( Status.WAIT_FOR_MARCHING,
                                    Status.PREVENT_BEING_KILLED,
                                    Status.HAS_ENEMY_BEHIND_BRICK )

                attackAction = battler.get_next_attack_action(route)
                realAction = self.try_make_decision(attackAction)
                if Action.is_stay(realAction): # 存在风险
                    if Action.is_move(attackAction):

                        # (inserted) 主动打破僵局：因为遇到敌人，为了防止被射杀而停留
                        #--------------------------
                        if (self.has_status_in_previous_turns(Status.WAIT_FOR_MARCHING, turns=1)
                            and self.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1)
                            ): # 即将停留第二回合
                            oppPlayer = Tank2Player(self._riskyEnemy)
                            if (oppPlayer.battler.canShoot # 当回合可以射击
                                and not oppPlayer.has_status_in_previous_turns(Status.RELOADING) # 上回合也可以射击
                                ): # 说明敌人大概率不打算攻击我
                                self.set_status(Status.KEEP_ON_MARCHING)
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
                                action = self.try_make_decision(battler.shoot_to(field))
                                if Action.is_shoot(action):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    self.set_status(Status.WAIT_FOR_MARCHING)
                                    self.set_status(Status.PREVENT_BEING_KILLED)
                                    returnAction = action
                                    raise OUTER_BREAK
                        #
                        # 如果能摧毁的是基地外墙，仍然选择攻击
                        # 因为在攻击后可能可以给出更加短的路线
                        #
                        for field in fields:
                            if battler.check_is_outer_wall_of_enemy_base(field):
                                action = self.try_make_decision(battler.shoot_to(field))
                                if Action.is_shoot(action):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    self.set_status(Status.WAIT_FOR_MARCHING)
                                    self.set_status(Status.PREVENT_BEING_KILLED)
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
                        if not self.has_status(Status.DEFENSIVE):
                            for field in fields:
                                if isinstance(field, BrickField):
                                    if battler.get_manhattan_distance_to(field) == 2: # 距离为 2 相当于土墙
                                        action = self.try_make_decision(battler.shoot_to(field))
                                        if Action.is_shoot(action):
                                            # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                            self.set_status(Status.WAIT_FOR_MARCHING)
                                            self.set_status(Status.PREVENT_BEING_KILLED)
                                            returnAction = action
                                            raise OUTER_BREAK

                    elif Action.is_shoot(attackAction):
                        # 如果为射击行为，检查是否是墙后敌人造成的
                        enemy = battler.get_enemy_behind_brick(attackAction)
                        if enemy is not None:
                            self._riskyEnemy = BattleTank(enemy) # 额外指定一下，确保是这个敌人造成的
                            self.set_status(Status.HAS_ENEMY_BEHIND_BRICK)


                    # 否则停止不前
                    # 此时必定有 riskyEnemy
                    #
                    self.set_status(Status.WAIT_FOR_MARCHING) # 可能触发 Signal.PREPARE_FOR_BREAK_BRICK 和 Signal.FORCED_MARCH
                    self.set_status(Status.PREVENT_BEING_KILLED) # TODO: 这个状态是普适性的，希望在上面的各种情况中都能补全
                    returnAction = Action.STAY
                    continue # 停留动作，尝试继续寻找

                # 对于移动行为，有可能处于闪避到远路又回来的僵局中 5cd009e0a51e681f0e8f3ffb
                # 因此在这里根据前期状态尝试打破僵局
                #----------------------------------
                if (self.has_status_in_previous_turns(Status.WILL_DODGE_TO_LONG_WAY, turns=1) # 说明上回合刚闪避回来
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
                            if battler.get_manhattan_distance_to(field) == 2:
                                action = self.try_make_decision(battler.shoot_to(field))
                                if Action.is_shoot(action):
                                    self.set_status(Status.KEEP_ON_MARCHING) # 真实体现
                                    returnAction = action
                                    raise OUTER_BREAK
                    # TODO:
                    #   还可以选择绕路？



                #
                # 禁止随便破墙！容易导致自己陷入被动！
                #
                if Action.is_shoot(realAction):
                    #
                    # 敌人处在墙后的水平路线上，并且与墙的间隔不超过 1 个空格 5cd33a06a51e681f0e91de95
                    # 事实上 1 个空格是不够的！ 5cd35e08a51e681f0e92182e
                    #
                    enemy = battler.get_enemy_behind_brick(realAction, interval=3)
                    if enemy is not None:
                        self.set_status(Status.HAS_ENEMY_BEHIND_BRICK)
                        self.set_status(Status.WAIT_FOR_MARCHING)
                        returnAction = Action.STAY
                        continue
                    #
                    # 敌人下一步可能移到墙后面
                    #
                    _shouldStay = False
                    for oppBattler in [ player.battler for player in self._opponents ]:
                        if oppBattler.destroyed:
                            continue
                        x1, y1 = oppBattler.xy
                        for x2, y2 in oppBattler.get_surrounding_empty_field_points():
                            moveAction = Action.get_move_action(x1, y1, x2, y2)
                            assert map_.is_valid_move_action(oppBattler, moveAction)
                            map_.simulate_one_action(oppBattler, moveAction)
                            if battler.get_enemy_behind_brick(realAction, interval=2) is not None: # 此时如果直接出现在墙的后面
                                map_.revert()
                                self.set_status(Status.WAIT_FOR_MARCHING)
                                returnAction = Action.STAY
                                _shouldStay = True
                                break
                            map_.revert()
                        if _shouldStay:
                            break
                    if _shouldStay:
                        continue

                # 否则继续攻击
                self.set_status(Status.KEEP_ON_MARCHING)
                returnAction = realAction
                raise OUTER_BREAK

            # endfor
        # endwith

        # 找到一个侵略性的行为
        if not Action.is_stay(returnAction):
            return returnAction

        # 否则返回 STAY
        self.set_status(Status.WAIT_FOR_MARCHING)
        return Action.STAY

#{ END }#
