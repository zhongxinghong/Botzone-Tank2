# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 03:01:59
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 04:23:46
"""
采用装饰器模式，对 TankField 进行包装，使之具有判断战场形势的能力

"""

__all__ = [

    "BattleTank",

    ]

from .global_ import np
from .utils import CachedProperty, debug_print, debug_pprint
from .action import Action
from .field import Field, SteelField, TankField, EmptyField, WaterField, BaseField, BrickField
from .strategy.utils import fake_map_matrix_T_without_enemy, fake_map_matrix_T_thinking_of_enemy_as_steel,\
                            get_manhattan_distance
from .strategy.route import INFINITY_ROUTE_LENGTH
from .strategy.search import find_shortest_route_for_move, find_shortest_route_for_shoot,\
                            find_all_routes_for_shoot, find_all_routes_for_move, get_searching_directions,\
                            get_searching_directions, DEFAULT_BLOCK_TYPES, DEFAULT_DESTROYABLE_TYPES


#{ BEGIN }#

class BattleTank(object):

    _instances = {} # { (side, id): instance }

    def __new__(cls, tank, map=None, **kwargs):
        """
        以 (side, id) 为主键，缓存已经创建过的作战对象
        使得该对象对于特定的 tank 对象为 Singleton
        """
        key = (tank.side, tank.id)
        obj = __class__._instances.get(key)
        if obj is None:
            map_ = map
            if map_ is None:
                raise ValueError("map is required at first initialization")
            obj = object.__new__(cls, **kwargs)
            __class__._instances[key] = obj
            obj._initialize(tank, map_) # 用自定义的函数初始化，而不是 __init__ ，为了防止单例被反复调用
        return obj

    def __init__(self, tank, map=None):
        pass

    def _initialize(self, tank, map):
        self._tank = tank
        self._map = map
        #self.__attackingRoute = None # 缓存变量 -> 为了支持地图回滚，将路线缓存暂时去掉了

    def __eq__(self, other):
        return self.side == other.side and self.id == other.id

    def __repr__(self):
        return "%s(%d, %d, %d, %d)" % (
                self.__class__.__name__, self.x, self.y, self.side, self.id)

    def __copy__(self):
        return self

    def __deepcopy__(self): # singleton !
        return self

    @property
    def field(self):
        return self._tank

    @property
    def tank(self):
        return self._tank

    @property
    def side(self):
        return self._tank.side

    @property
    def id(self):
        return self._tank.id

    @property
    def x(self):
        return self._tank.x

    @property
    def y(self):
        return self._tank.y

    @property
    def xy(self):
        return self._tank.xy

    @property
    def destroyed(self):
        return self._tank.destroyed

    @property
    def canShoot(self): # 本回合是否可以射击
        return not Action.is_shoot(self._tank.previousAction)

    def is_in_our_site(self):
        """
        是否处于我方半边的地图，不包含中线
        """
        base = self._map.bases[self.side]
        return ( np.abs( self.y - base.y ) < 4 )

    def is_in_enemy_site(self):
        """
        是否处于地方半边的地图，包含中线
        """
        return not self.is_in_our_site()

    def get_surrounding_empty_field_points(self, **kwargs):
        """
        获得周围可以移动到达的空位
        """
        tank = self._tank
        map_ = self._map
        x, y = tank.xy
        points = []
        for dx, dy in get_searching_directions(x, y, **kwargs):
            x3 = x + dx
            y3 = y + dy
            if not map_.in_map(x3, y3):
                continue
            fields = map_[x3, y3]
            if len(fields) == 0:
                points.append( (x3, y3) )
            elif len(fields) > 2:
                continue
            else:
                field = fields[0]
                if isinstance(field, EmptyField):
                    points.append( (x3, y3) )
                else:
                    continue
        return points

    def get_all_valid_move_action(self, **kwargs):
        """
        所有合法的移动行为
        """
        tank = self._tank
        map_ = self._map
        actions = []
        x1, y1 = tank.xy
        for x2, y2 in self.get_surrounding_empty_field_points(**kwargs):
            moveAction = Action.get_move_action(x1, y1, x2, y2)
            map_.is_valid_move_action(tank, moveAction)
            actions.append(moveAction)
        return actions

    def get_all_valid_shoot_action(self):
        """
        获得所有合法的射击行为
        """
        if self.canShoot:
            return list(Action.SHOOT_ACTIONS)
        else:
            return []

    def get_all_valid_actions(self):
        """
        获得所有合法的行为
        """
        return self.get_all_valid_move_action() + self.get_all_valid_shoot_action() + [ Action.STAY ]

    def get_all_shortest_attacking_routes(self, ignore_enemies=True, bypass_enemies=False, delay=0, **kwargs):
        """
        获得所有最短的进攻路线

        Input:
            - ignore_enemies   bool   是否将敌人视为空
            - bypass_enemies   bool   是否将敌人视为 SteelField 然后尝试绕过他0
            - delay            int    允许与最短路线延迟几步

            WARNING: ignore_enemies 与 bypass_enemies 为互斥选项，至多选择一个

        Yield From:
            - routes    [Route]

        """
        if ignore_enemies and bypass_enemies:
            raise ValueError("you can't think of enemies as steel and air at the same time")

        map_    = self._map
        tank    = self._tank
        side    = tank.side
        oppSide = 1- tank.side
        oppBase = map_.bases[oppSide]

        if ignore_enemies:
            matrix_T = fake_map_matrix_T_without_enemy(map_, tank.side)
        elif bypass_enemies:
            matrix_T = fake_map_matrix_T_thinking_of_enemy_as_steel(map_, tank.side)
        else:
            matrix_T = map_.matrix_T

        routes = find_all_routes_for_shoot(
                        tank.xy,
                        oppBase.xy,
                        matrix_T,
                        block_types=DEFAULT_BLOCK_TYPES+(
                            Field.BASE + 1 + side,
                            Field.TANK + 1 + side, # 队友有可能会变成阻碍！ 5cdde41fd2337e01c79f1284
                            Field.MULTI_TANK,
                        ),
                        destroyable_types=DEFAULT_DESTROYABLE_TYPES+(
                            Field.BASE + 1 + oppSide,
                            # 不将敌方坦克加入到其中
                        ),
                        **kwargs)

        minLength = INFINITY_ROUTE_LENGTH

        for route in routes:
            if not route.is_not_found():
                if minLength == INFINITY_ROUTE_LENGTH:
                    minLength = route.length # 初始化 minLength
                if route.length - minLength > delay:
                    break
                yield route
            else: # 否则就是 [ Route() ] 表示没有找到路径
                yield route
                break


    def get_shortest_attacking_route(self, *args, **kwargs):
        """
        获得默认的最短攻击路径
        """
        for route in self.get_all_shortest_attacking_routes(*args, **kwargs):
            return route # 直接返回第一个 route


    def get_next_attack_action(self, route=None):
        """
        下一个进攻行为，不考虑四周的敌人

        Input:
            - route   Route   自定义的攻击路径
                              默认为 None ，使用默认的最短路径
        """
        tank    = self._tank
        map_    = self._map
        oppBase = map_.bases[1 - tank.side]

        if route is None:
            route = self.get_shortest_attacking_route()

        if route.is_not_found(): # 没有找到路线，这种情况不可能
            return Action.STAY
        elif route.length == 0: # 说明 start 和 end 相同，已经到达基地，这种情况也不可能
            return Action.STAY

        x1, y1 = tank.xy
        x3, y3 = route[1].xy # 跳过 start
        action = Action.get_action(x1, y1, x3, y3) # move-action
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action]

        ## 优先移动 ##
        if map_.is_valid_move_action(tank, action):
            # 但是，如果正前方就是基地，则不移动，只射击
            x, y = tank.xy
            while True:
                x += dx
                y += dy
                if not map_.in_map(x, y):
                    break
                fields = map_[x, y]
                if len(fields) == 0:
                    continue
                elif len(fields) > 1:
                    break
                else:
                    field = fields[0]
                    if isinstance(field, (WaterField, EmptyField) ):
                        continue
                    elif isinstance(field, SteelField):
                        break # 钢墙不可以射穿
                    elif isinstance(field, BrickField): # 土墙认为可以射掉
                        continue
                    elif isinstance(field, TankField): # 坦克也认为可以射掉
                        if field.side == tank.side:
                            break # 队友坦克不进攻
                        continue  # 敌方坦克在此处不应该出现，他们应该在上游的决策中被考虑到
                    elif field is oppBase:
                        if self.canShoot: # 这个时候如果能够射击，就优先射击
                            return action + 4
                    else:
                        continue
            # 其他情况仍然优先移动
            return action

        ## 遇到墙/敌方基地/坦克，不能移动
        if self.canShoot: # 尝试射击
            action += 4
            for field in self.get_destroyed_fields_if_shoot(action):
                if isinstance(field, TankField) and field.side == tank.side:
                    return Action.STAY # 仅需要防止射到队友
            return action

        return Action.STAY # 不能射击，只好等待


    def get_shortest_route_to_enemy(self, oppTank):
        """
        查找射杀敌方的最短路线
            TODO: 可能需要判断水路

        尚没有被使用过
        """
        tank = self._tank
        map_ = self._map
        side = tank.side
        oppSide = 1 - side
        route = find_shortest_route_for_shoot(
                            tank.xy,
                            oppTank.xy,
                            map_.matrix_T, # 正常地图
                            block_types=DEFAULT_BLOCK_TYPES+(
                                Field.BASE + 1 + side,
                                Field.TANK + 1 + side,
                                Field.MULTI_TANK,
                            ),
                            destroyable_types=DEFAULT_DESTROYABLE_TYPES+(
                                Field.BASE + 1 + oppSide,
                                Field.TANK + 1 + oppSide, # 加入地方坦克
                            ),
                            x_axis_first=True, # 优先左右拦截
                            )
        return route


    def get_route_to_enemy_by_movement(self, oppTank, block_teammate=True):
        """
        近身条件下，获得到达对方的路劲
        """
        tank = self._tank
        map_ = self._map
        side = tank.side

        if block_teammate: # 将己方坦克和重叠坦克视为 block
            block_types = DEFAULT_BLOCK_TYPES+(
                                Field.BASE + 1 + side,
                                Field.TANK + 1 + side,
                                Field.MULTI_TANK,
                            )
        else:
            block_types = DEFAULT_BLOCK_TYPES+(
                                Field.BASE + 1 + side,
                            )

        route = find_shortest_route_for_move(
                            tank.xy,
                            oppTank.xy,
                            map_.matrix_T,
                            block_types=block_types,
                            x_axis_first=True, # 优先左右拦截
                            )
        return route


    def get_next_hunting_action(self, oppTank):
        """
        下一个追杀敌军的行为
        """
        tank = self._tank
        map_ = self._map
        side = tank.side
        oppSide = 1 - side

        route = self.get_shortest_route_to_enemy(oppTank)

        if route.is_not_found(): # 没有找到路线，这种情况不可能
            return Action.STAY
        elif route.length == 0: # 说明自己和敌方重合，这种情况不应该出现
            return Action.STAY

        x1, y1 = tank.xy
        x3, y3 = route[1].xy # 跳过 start
        action = Action.get_action(x1, y1, x3, y3) # move-action
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action]

        ## 见到敌人就开火，否则移动
        shootAction = action + 4
        destroyedFields = [] # 会被用到两次，因此缓存一下
        if self.canShoot:
            destroyedFields = self.get_destroyed_fields_if_shoot(action)
            for field in destroyedFields:
                if isinstance(field, TankField) and field.side == side: # 有队友，停止射击
                    break
            else: # 否则再判断是否应该射击
                for field in destroyedFields:
                    if isinstance(field, TankField) and field.side == oppSide:
                        return shootAction
            # 到此处说明没有敌人，或者有队友

        ## 优先移动
        if map_.is_valid_move_action(tank, action):
            return action

        ## 遇到路障，射击
        if self.canShoot:
            for field in destroyedFields:
                if isinstance(field, TankField) and field.side == side:
                    return Action.STAY # 遇到队友，等待
            return shootAction

        ## 也不能射击？于是等待
        return Action.STAY


    def get_manhattan_distance_to(self, field):
        """
        获得自身到 field 的曼哈顿距离，不考虑中间地形
        通常用于判断 field 与自身距离是否为 2 ，也就是中间相隔一个格子

        Input:
            - field     Field/BattleTank/...     具有 xy, x, y 属性的 field 对象
        """
        x1, y1 = self.xy
        x2, y2 = field.xy
        return get_manhattan_distance(x1, y1, x2, y2)


    def get_enemies_around(self):
        """
        返回获得身边的 tank 可能有多架

        WARNING:
            这个函数可以返回空值，也就是没有任何敌人在身旁的时候也可以使用
            如果需要知道 enemies 是谁，那么建议直接调用这个函数来确定身边情况

        Return:
            - tanks    [TankField]/[]
        """
        tank = self._tank
        map_ = self._map
        x1, y1 = tank.xy

        enemies = []

        for dx, dy in get_searching_directions(x1, y1):
            x, y = tank.xy
            while True:
                x += dx
                y += dy
                if not map_.in_map(x, y):
                    break
                currentFields = map_[x, y]
                if len(currentFields) == 0: # 没有对象
                    continue
                elif len(currentFields) > 1: # 多辆坦克
                    for field in currentFields:
                        if isinstance(field, TankField) and field.side != tank.side:
                            enemies.append(field)
                else: # len == 1
                    field = currentFields[0]
                    if isinstance(field, (EmptyField, WaterField) ):
                        continue
                    elif not isinstance(field, TankField): # 说明这个方向上没有敌人
                        break
                    elif field.side != tank.side: # 遇到了敌人
                        enemies.append(field)
                    else: # 遇到了队友
                        break

        return enemies


    def has_enemy_around(self):
        """
        周围是否存在敌军
        """
        return len(self.get_enemies_around()) > 0


    def has_overlapping_enemy(self):
        """
        是否与敌方坦克重合
        """
        map_ = self._map
        tank = self._tank
        onSiteFields = map_[tank.xy]
        for field in onSiteFields:
            assert isinstance(field, TankField), "unexpected field %r" % field
            if field.side != tank.side:
                return True
        return False


    def get_overlapping_enemy(self):
        """
        获得与自身重叠的坦克
        认为一般只与一架坦克重合，所以返回遇到的第一辆坦克

        WARNING:
            - 这个函数调用前，必须先检查是否有重叠的敌人

        Return:
            - tank    TankField
        """
        map_ = self._map
        tank = self._tank
        onSiteFields = map_[tank.xy]
        for field in onSiteFields:
            if field.side != tank.side:
                return field
        raise Exception("no overlapping enemy was found")


    def try_dodge(self, oppTank):
        """
        尝试回避对方 tank

        Input:
            - oppTank   TankField/BattleTank    能够通过 x, y, xy 获取坐标值的坦克对象

        Return:
            - actions    [int]    能够闪避开的行为值，可能为空

        """
        tank = self._tank
        map_ = self._map
        side = tank.side
        oppSide = 1 - side
        base = map_.bases[side]
        oppBase = map_.bases[oppSide]
        x1, y1 = tank.xy
        x2, y2 = oppTank.xy
        if self.is_in_our_site():
            x3, y3 = base.xy     # 在本方地盘，优先朝自己基地的方向闪现
        else:
            x3, y3 = oppBase.xy  # 在对方地盘，优先朝着对方基地的方向闪现
        actions = []
        for dx, dy in get_searching_directions(x1, y1, x3, y3, middle_first=True): # 优先逃跑向对方基地
            x4 = x1 + dx
            y4 = y1 + dy
            if x4 == x2 or y4 == y2: # 逃跑方向不对
                continue
            action = Action.get_action(x1, y1, x4, y4)
            if map_.is_valid_move_action(tank, action):
                actions.append(action)
        return actions


    def can_dodge(self):
        """
        当前地形是否拥有闪避的机会，用于判断是否处在狭路，与 len( try_dodge ) > 0 不等价
        """
        tank = self._tank
        map_ = self._map
        x, y = self._tank.xy

        actions = []

        for dx, dy in get_searching_directions(x, y):
            x3 = x + dx
            y3 = y + dy
            moveAction = Action.get_action(x, y, x3, y3)
            if map_.is_valid_move_action(moveAction):
                actions.append(moveAction)

        if len(actions) < 2: # 不可能闪避
            return False
        if len(actions) >= 3: # 可以
            return True

        assert len(actions) == 2
        return not Action.is_opposite(*actions) # 相反方向，无法闪避，否则可以


    def break_brick_for_dodge(self, oppTank):
        """
        尝试凿开两边墙壁，以闪避敌人进攻

        适用条件：
            自己处在 WAIT_FOR_MARCHING 状态，身边没有遇敌的时候
        """
        tank = self._tank
        map_ = self._map
        side = tank.side
        oppSide = 1 - side
        base = map_.bases[side]
        oppBase = map_.bases[oppSide]
        x1, y1 = tank.xy
        x2, y2 = oppTank.xy
        if self.is_in_our_site(): # 选择性同 try_dodge
            x3, y3 = base.xy
        else:
            x3, y3 = oppBase.xy
        actions = []
        for dx, dy in get_searching_directions(x1, y1, x3, y3, middle_first=True):
            # 按照惯例，优先凿开移向对方基地的墙
            x3 = x1 + dx
            y3 = y1 + dy
            if x3 == x2 or y3 == y2: # 方向不对，不能凿开相隔的墙
                continue
            # 需要判断两边的墙壁是否为不可凿开的对象
            if not map_.in_map(x3, y3):
                continue
            fields = map_[x3, y3]
            assert len(fields) == 1, "not suit for current situation"
            field = fields[0]
            if isinstance(field, BrickField):
                action = Action.get_action(x1, y1, x3, y3) + 4 # 射击行为一定成功
                actions.append(action)
            else: # 其他都是不适用的
                continue
        return actions


    def move_to(self, oppTank):
        """
        返回 self -> oppTank 的移动

        Input:
            oppTank   TankField/BattleTank    所有带坐标的 tank 对象
        """
        x1, y1 = self._tank.xy
        x2, y2 = oppTank.xy
        assert x1 == x2 or y1 == y2, "can't be used when two tanks are not in line"
        return Action.get_action(x1, y1, x2, y2)


    def shoot_to(self, oppTank):
        """
        返回 self -> oppTank 的射击行为，相当于 move + 4
        """
        return self.move_to(oppTank) + 4


    def on_the_same_line_with(self, oppTank, ignore_brick=True):
        """
        是否和敌人处在同一条直线上

        Input:
            oppTank        TankField/BattleTank    所有带坐标的 tank 对象
            ignore_brick   bool    是否忽略土墙的阻挡

        """
        tank = self._tank
        map_ = self._map
        x1, y1 = tank.xy
        x2, y2 = oppTank.xy

        if x1 != x2 and y1 != y2: # 坐标上直接可以否掉的情况
            return False
        elif (x1, y1) == (x2, y2): # 重叠，这种情况一般不会出现，但是还是判断一下
            return True

        if x1 == x2:
            dx = 0
            dy = np.sign(y2 - y1)
        elif y1 == y2:
            dx = np.sign(x2 - x1)
            dy = 0

        x, y = tank.xy
        while True:
            x += dx
            y += dy
            if not map_.in_map(x, y):
                break
            fields = map_[x, y]
            if len(fields) == 0:
                continue
            elif len(fields) == 2:
                if oppTank.xy == (x, y): # 说明敌方坦克在多人坦克里
                    return True
                else: # 否则不算
                    return False
            else:
                field = fields[0]
                if isinstance(field, (EmptyField, WaterField) ):
                    continue
                elif isinstance(field, BrickField):
                    if ignore_brick: # 这种情况将 brick 视为空
                        continue
                    else:
                        return False
                elif isinstance(field, TankField) and field.xy == oppTank.xy:
                    return True
                else:
                    return False # 其他所有的 block 类型均视为 False

        # 没有检查到受阻的情况，那么就是在同一条直线上了
        return True


    def back_away_from(self, oppTank):
        """
        背向远离地方坦克
        """
        return (self.move_to(oppTank) + 2) % 4  # 获得相反方向


    def get_destroyed_fields_if_shoot(self, action):
        """
        如果向 action 对应的方向射击，那么可以摧毁什么东西？
        ------------------------------------------------------------
        主要用于 move 不安全而又不想白白等待的情况，尝试采用进攻开路
        也可以用于其他问题的判断

        Input:
            - action   int   原始的移动行为（虽然事实上也可以是射击 :)

        Return:
            - fields   [Field]   将被摧毁的对象
        """
        assert Action.is_move(action) or Action.is_shoot(action)
        tank = self._tank
        map_ = self._map

        action %= 4
        x, y = tank.xy
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action]
        while True:
            x += dx
            y += dy
            if not map_.in_map(x, y):
                break
            fields = map_[x, y]
            if len(fields) == 0: # 没有对象
                continue
            elif len(fields) > 1: # 多辆坦克
                return fields
            else:
                field = fields[0]
                if isinstance(field, (WaterField, EmptyField) ):
                    continue
                elif isinstance(field, SteelField):
                    return []
                else:
                    return fields
        return []


    def is_face_to_enemy_base(self, ignore_brick=False):
        """
        是否直面对方基地，或者是与敌人基地处在同一条直线上

        Input:
            - ignore_brick   bool   是否忽略土墙，如果忽略，那么只需要基地和坦克
                                    处在同一直线上即可
        """
        tank = self._tank
        map_ = self._map
        oppSide = 1 - tank.side
        oppBase = map_.bases[oppSide]

        x1, y1 = tank.xy
        x2, y2 = oppBase.xy
        for dx, dy in get_searching_directions(x1, y1, x2, y2):
            x, y = tank.xy
            while True:
                x += dx
                y += dy
                if not map_.in_map(x, y):
                    break
                fields = map_[x, y]
                if len(fields) == 0:
                    continue
                elif len(fields) > 1:
                    break # 两个坦克
                else:
                    field = fields[0]
                    if isinstance(field, (WaterField, EmptyField) ):
                        continue # 非 block 情况
                    elif isinstance(field, BrickField):
                        if ignore_brick:
                            continue
                        else:
                            break
                    elif field is oppBase:
                        return True
                    else:
                        break

        return False


    def get_enemy_behind_brick(self, action, interval=0):
        """
        返回行为对应的方向后的围墙后的敌人

        乙方坦克和围墙间可以有任意空位
        围墙到敌方坦克间至多有 interval 个空位

        Input:
            - action     int   移动/射击行为，确定方向
            - interval   int   最远检查到距离墙多远的位置？
                               interval = 0 表示只检查最靠近墙的那个位置
                               特殊地 interval = -1 表示不限制 interval

        Return:
            - tank    TankField/None    敌人对应的 tank 对象，多个敌人只返回一个
                                        情况不符则返回 None
        """
        tank = self._tank
        map_ = self._map

        x1, y1 = tank.xy
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action % 4]

        # 检查前方是否是墙
        x2, y2 = x1, y1
        while True:
            x2 += dx
            y2 += dy
            if not map_.in_map(x2, y2):
                return None
            fields = map_[x2, y2]
            if len(fields) == 0:
                continue
            elif len(fields) > 1:
                return None
            else:
                field = fields[0]
                if isinstance(field, BrickField):
                    break # 此时 x2, y2 位置上是一个 Brick
                elif isinstance(field, (WaterField, EmptyField) ):
                    continue
                else:
                    return None

        # 检查前方是否有敌方坦克
        x3, y3 = x2, y2
        currentInterval = -1
        while True:
            currentInterval += 1
            if interval != -1 and currentInterval > interval:
                break
            x3 += dx
            y3 += dy
            if not map_.in_map(x3, y3):
                break
            fields = map_[x3, y3]
            if len(fields) == 0:
                continue
            elif len(fields) > 1:
                for field in fields:
                    if isinstance(field, TankField) and field.side != tank.side:
                        return field
            else:
                field = fields[0]
                if isinstance(field, TankField) and field.side != tank.side:
                    return field
                elif isinstance(field, (WaterField, EmptyField) ):
                    continue
                else: # 除了水路和空地可以继续搜索外，其他情况均直接结束
                    break

        return None


    def has_enemy_behind_brick(self, action):
        return self.get_enemy_behind_brick(action) is not None


    def get_nearest_enemy(self): #, block_teammate=False, isolate=False):
        """
        获得最近的敌人，移动距离

        Input:
            - isolate   bool    是否只考虑离自己最近，而不从团队整体考虑
                                如果联系整个团队，那么离自己最近的敌人定义为与我之间间隔的步数
                                和与我的队友之间间隔的步数差最小的敌人

        Return:
            - enemy   TankField

        """
        '''tank = self._tank
        map_ = self._map

        _enemies = map_.tanks[1 - tank.side]
        enemies = [ enemy for enemy in _enemies if not enemy.destroyed ] # 已经被摧毁的敌人就不考虑了

        if len(enemies) == 0: # 胜利？
            return None
        if len(enemies) < 2:
            return enemies[0]

        # TODO:
        #   两种情况的决策顺序是有差别的，一个是见到走不通就 block_teammate = False 另一个是如果全部都走不通
        #   就全部 block_teammate = False ，这可能会引发问题？
        if not isolate:
            #
            # 注：这是一个糟糕的设计，因为 BattleTank 对象最初被设计为只懂得单人决策的对象
            # 他不应该知道队友的行为，但是此处打破了这个规则
            #
            teammate = BattleTank( map_.tanks[tank.side][ 1 - tank.id ] )
            if teammateBattler.destroyed:
                pass
            else:
                deltaLengthWithEnemyList = []
                for enemy in enemies:
                    route1 = self.get_route_to_enemy_by_movement(enemy)
                    if route1.is_not_found():
                        route1 = self.get_route_to_enemy_by_movement(enemy, block_teammate=False)
                        if route1.is_not_found(): # 我无法到达敌人的位置？？？
                            continue
                    route2 = teammateBattler.get_route_to_enemy_by_movement(enemy)
                    if route2.is_not_found():
                        route2 = teammateBattler.get_route_to_enemy_by_movement(enemy, block_teammate=False)

                    if route2.is_not_found():
                        deltaLength = route1.length # 这样做是否合理？
                    else:
                        deltaLength = route1.length - route2.length
                    deltaLengthWithEnemyList.append( (deltaLength, enemy) )
                    idx = deltaLengthWithEnemyList.index(
                                    min(deltaLengthWithEnemyList, key=lambda tup: tup[0]) )
                    return deltaLengthWithEnemyList[idx][1]


        # 否则为单人决策

        routes = [ self.get_route_to_enemy_by_movement(enemy) for enemy in enemies ]

        if all( route.is_not_found() for route in routes ): # 均不可到达？
            routes = [ self.get_route_to_enemy_by_movement(enemy, block_teammate=False)
                            for enemy in enemies ] # 因为队友阻塞 ?

        routeWithEnemyList = [
            (route, enemy) for route, enemy in zip(routes, enemies)
                                    if not route.is_not_found() # 队友阻塞导致 -1 需要去掉
        ]

        idx = routeWithEnemyList.index(
                    min(routeWithEnemyList, key=lambda tup: tup[0].length) )

        return routeWithEnemyList[idx][1]'''
        tank = self._tank
        map_ = self._map

        enemies = [ enemy for enemy in map_.tanks[1 - tank.side]
                            if not enemy.destroyed ] # 已经被摧毁的敌人就不考虑了

        battler = self
        teammate = BattleTank( map_.tanks[tank.side][ 1 - tank.id ] )

        if not teammate.destroyed:
            return min( enemies, key=lambda enemy:
                    battler.get_manhattan_distance_to(enemy) - teammate.get_manhattan_distance_to(enemy)
                ) # 综合队友的情况进行考虑，对方离我近，同时离队友远，那么那么更接近于我
        else:
            return min( enemies, key=lambda enemy: battler.get_manhattan_distance_to(enemy) )


    def check_is_outer_wall_of_enemy_base(self, field, layer=2):
        """
        检查一个 field 是否为敌方基地的外墙
        外墙被视为基地外的 layer 层 Brick
        """
        if not isinstance(field, BrickField):
            return False
        map_ = self._map
        tank = self._tank
        oppBase = map_.bases[1 - tank.side]
        x1, y1 = oppBase.xy
        x2, y2 = field.xy
        return ( np.abs( x1 - x2 ) <= layer and np.abs( y1 - y2 ) <= layer )


#{ END }#