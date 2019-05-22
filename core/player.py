# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 00:35:10
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-21 21:04:43
"""
游戏玩家，操作着一架坦克，充当单人决策者

"""

__all__ = [

    "Tank2Player",

    ]

from .global_ import np
from .utils import debug_print, debug_pprint
from .action import Action
from .field import TankField
from .tank import BattleTank
from .strategy.signal import Signal
from .strategy.status import Status
from .decision.abstract import DecisionMaker
from .decision import DecisionChain, MarchingDecision, ActiveDefenseDecision, BaseDefenseDecision,\
    OverlappingDecision, EncountEnemyDecision, AttackBaseDecision, LeaveTeammateDecision,\
    BehindBrickDecision

#{ BEGIN }#

class Player(DecisionMaker):

    UNHANDLED_RESULT = Action.INVALID  # 不能处理的情况，返回 Action.INVALID

    def __init__(self, *args, **kwargs):
        if __class__ is self.__class__:
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
        self._status = set()    #　当前回合的状态，可以有多个，每回合情况
        self._labels = set()    # 对手给我做的标记，标记后长期有效
        self._riskyEnemy = None # 缓存引起潜在风险的敌人 BattleTank
        self._decision = None   # 缓存最终的决策

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

    @property
    def opponents(self):
        return self._opponents


    def set_team(self, team):
        self._team = team

    def set_teammate(self, player): # -> Tank2Player
        assert isinstance(player, Tank2Player) and player.side == self.side
        self._teammate = player

    def set_opponents(self, opponents): # -> [Tank2Player]
        for player in opponents:
            assert isinstance(player, Tank2Player) and player.side != self.side
        self._opponents = opponents

    def get_risk_enemy(self):
        return self._riskyEnemy

    def set_risk_enemy(self, enemy):
        self._riskyEnemy = BattleTank(enemy) # 确保为 BattleTank 对象

    def get_current_decision(self): # 返回已经做出的决策
        return self._decision

    def change_current_decision(self, action): # 团队用来修改队员当前决策的缓存
        self._decision = action

    def get_status(self):
        return self._status

    def set_status(self, *status): # 添加一个或多个状态
        for _status in status:
            self._status.add(_status)

    def remove_status(self, *status): # 删除一个或多个状态
        for _status in status:
            self._status.discard(_status) # remove_if_exists

    def clear_status(self): # 清除所有状态
        self._status.clear()

    def has_status(self, status): # 是否存在某种状态
        return status in self._status

    def get_labels(self):
        return self._labels

    def add_labels(self, *labels): # 添加一个或多个标记
        for label in labels:
            self._labels.add(label)

    def has_label(self, label): # 是否存在某个标记
        return label in self._labels

    def remove_labels(self, *labels): # 删除一个活多个标记
        for label in labels:
            self._labels.discard(label)

    def clear_labels(self): # 清楚全部标记
        self._labels.clear()

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
            oppBattlers = [ _player.battler for _player in self._opponents ]
            riskFreeOpps = []
            for oppBattler in oppBattlers:
                if not oppBattler.canShoot: # 对手本回合无法射击，则不必担心
                    riskFreeOpps.append(oppBattler)
            with map_.simulate_one_action(tank, action): # 提交地图模拟情况
                for oppBattler in oppBattlers:
                    if oppBattler.destroyed:
                        continue
                    elif oppBattler in riskFreeOpps:
                        continue
                    for enemy in oppBattler.get_enemies_around():
                        if enemy is tank:
                            self._riskyEnemy = oppBattler
                            return False

        # 射击情况下有两种可能的危险
        #--------------------------
        # 1. 打破一堵墙，然后敌人在后面等着
        # 2. 身边没有闪避的机会，打破一堵墙，对方刚好从旁路闪出来
        #---------------------------
        if Action.is_shoot(action):
            destroyedFields = battler.get_destroyed_fields_if_shoot(action)
            with map_.simulate_one_action(battler, action): # 模拟本方行为
                #
                # TODO:
                #   只模拟一个坦克的行为并不能反映真实的世界，因为敌方这回合很有可能射击
                #   那么下回合它就无法射击，就不应该造成威胁
                #
                for oppTank in map_.tanks[1 - tank.side]:
                    if oppTank.destroyed:
                        continue
                    oppBattler = BattleTank(oppTank)
                    for oppAction in Action.MOVE_ACTIONS: # 任意移动行为
                        if not map_.is_valid_action(oppTank, oppAction):
                            continue
                        with map_.simulate_one_action(oppTank, oppAction): # 模拟敌方行为
                            for field in destroyedFields:
                                if field.xy == oppTank.xy:
                                    break # 对方下一步不可能移动到我即将摧毁的 field 上，所以这种情况是安全的
                            else:
                                for enemy in oppBattler.get_enemies_around():
                                    if enemy is tank: # 敌方原地不动或移动一步后，能够看到该坦克
                                        # 还可以尝试回避
                                        actions = battler.try_dodge(oppBattler)
                                        if len(actions) == 0: # 无法回避，危险行为
                                            self._riskyEnemy = oppBattler
                                            return False

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
            for _oppBattler in [ _player.battler for _player in self._opponents ]: # 找到另一个敌人
                if _oppBattler.destroyed: # 输了就不算
                    continue
                if _oppBattler is oppBattler: # 排除目前这个敌人
                    continue
                if not _oppBattler.canShoot: # 本回合不能攻击的不算
                    continue
                # 开始模拟，反正就一架坦克
                with map_.simulate_one_action(tank, action):
                    for enemy in _oppBattler.get_enemies_around():
                        if enemy is tank: # 我方坦克将出现在它旁边，并且它可以射击
                            self._riskyEnemy = _oppBattler
                            return False # 可能被偷袭

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
        battler = self._battler
        if not map_.is_valid_move_action(tank, action): # 还是检查一下，不要出错
            return False

        # 如果移动后有两个敌人在旁边，那么不能前进 5cd3e7a786d50d05a0082a5d
        #-------------------------------------------
        with map_.simulate_one_action(tank, action):
            if len(battler.get_enemies_around()) > 1:
                #self._riskyEnemy = ??
                return False

        _oppBattlers = [ _player.battler for _player in self._opponents ]

        for _oppBattler in _oppBattlers:
            if _oppBattler.destroyed: # 跳过已经输了的
                continue
            if not _oppBattler.canShoot: # 另一个对手不能射击
                continue
            if _oppBattler is oppBattler: # 不考虑和自己重叠的这个坦克
                continue
            with map_.simulate_one_action(tank, action): # 提交模拟
                for enemy in _oppBattler.get_enemies_around():
                    if enemy is tank: # 不安全，可能有风险
                        self._riskyEnemy = _oppBattler
                        return False
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

    # @override
    def make_decision(self, signal=Signal.NONE):
        """
        预处理：
        ------------------
        - 清除所有旧有状态
        - 清除可能的风险敌人
        - 统一处理回复格式

        注意:
        ------------------
        - 申明为 _make_decision 过程中的缓存变量，必须在下一次决策前预先清除

        """
        self.clear_status()     # 先清除所有的状态
        self._riskyEnemy = None # 清楚所有缓存的风险敌人

        res = self._make_decision(signal)

        if isinstance(res, (tuple, list)) and len(res) == 2:
            returnSignal = res[1]
            action = res[0]
        else:
            if signal != Signal.NONE: # 说明没有回复团队信号
                returnSignal = Signal.UNHANDLED
            else:
                returnSignal = Signal.INVALID
            action = res

        self._decision = action # 缓存决策
        return ( action, returnSignal )


    def _make_decision(self, signal):

        battler  = self._battler

        if self.defeated:
            self.set_status(Status.DIED)
            return self.__class__.UNHANDLED_RESULT

        if not battler.canShoot:
            self.set_status(Status.RELOADING)


        decisions = DecisionChain(

                    LeaveTeammateDecision(self, signal),
                    AttackBaseDecision(self, signal),
                    EncountEnemyDecision(self, signal),
                    OverlappingDecision(self, signal),
                    BaseDefenseDecision(self, signal),
                    BehindBrickDecision(self, signal),
                    ActiveDefenseDecision(self, signal),
                    MarchingDecision(self, signal),

                )


        res = decisions.make_decision()

        if decisions.is_handled(res):
            return res

        return self.__class__.UNHANDLED_RESULT

#{ END }#
