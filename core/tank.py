# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 03:01:59
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-02 16:21:56
"""
采用装饰器模式，对 TankField 进行包装，使之具有判断战场形势的能力

"""

__all__ = [

    "BattleTank",

    ]

from .global_ import np
from .utils import CachedProperty, debug_print
from .action import Action
from .field import Field, SteelField, TankField, EmptyField, WaterField, BaseField, BrickField
from .strategy.utils import fake_map_matrix_T_without_enemy
from .strategy.search import find_shortest_route_for_shoot, find_shortest_route_for_move,\
        get_route_length, get_searching_directions, DEFAULT_BLOCK_TYPES, DEFAULT_DESTROYABLE_TYPES,\
        INFINITY_ROUTE_LENGTH


#{ BEGIN }#

class BattleTank(object):

    _instances = {} # { (side, id): instance }

    def __new__(cls, tank, map=None, *args, **kwargs):
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
            obj = super(BattleTank, cls).__new__(cls, *args, **kwargs)
            __class__._instances[key] = obj
            ## BattleTank.__init__(obj, tank, map) # 在此处初始化
            obj._tank = tank
            obj._map = map_
            obj.__attackingRoute = None
            ## END BattleTank.__init__
        return obj

    def __init__(self, tank, map=None):
        '''self._tank = tank
        self._map = map
        self.__attackingRoute = None # 缓存变量'''
        pass

    def __repr__(self):
        return "%s(%d, %d, %d, %d)" % (
                self.__class__.__name__, self.x, self.y, self.side, self.id)

    @property
    def field(self):
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


    def get_shortest_attacking_route(self, ignore_enemies=True):
        """
        获得最短进攻路线

        Input:

            - ignore_enemies    bool    是否将敌人视为空

        """
        if self.__attackingRoute is not None: # 缓存
            return self.__attackingRoute

        map_    = self._map
        tank    = self._tank
        side    = tank.side
        oppSide = 1- tank.side
        oppBase = map_.bases[oppSide]

        if ignore_enemies:
            matrix_T = fake_map_matrix_T_without_enemy(map_, tank.side)
        else:
            matrix_T = map_.matrix_T

        route = find_shortest_route_for_shoot(
                        tank.xy,
                        oppBase.xy,
                        matrix_T,
                        block_types=DEFAULT_BLOCK_TYPES+(
                            Field.BASE + 1 + side,
                            Field.TANK + 1 + side,
                            Field.MULTI_TANK,
                        ),
                        destroyable_types=DEFAULT_DESTROYABLE_TYPES+(
                            Field.BASE + 1 + oppSide,
                            # 不将敌方坦克加入到其中
                        ))

        self.__attackingRoute = route
        return route


    def get_next_attack_action(self):
        """
        下一个进攻行为，不考虑四周的敌人
        """
        tank    = self._tank
        map_    = self._map
        oppBase = map_.bases[1 - tank.side]

        route = self.get_shortest_attacking_route()

        if get_route_length(route) == INFINITY_ROUTE_LENGTH: # 没有找到路线，这种情况不可能
            return Action.STAY
        elif get_route_length(route) == 0: # 说明 start 和 end 相同，已经到达基地，这种情况也不可能
            return Action.STAY

        x1, y1 = tank.xy
        x3, y3, _, _ = route[1] # 跳过 start
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

        if get_route_length(route) == INFINITY_ROUTE_LENGTH: # 没有找到路线，这种情况不可能
            return Action.STAY
        elif get_route_length(route) == 0: # 说明自己和敌方重合，这种情况不应该出现
            return Action.STAY

        x1, y1 = tank.xy
        x3, y3, _, _ = route[1] # 跳过 start
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


    def has_enemy_around(self):
        """
        周围是否存在敌军
        """
        tank = self._tank
        map_ = self._map
        x1, y1 = tank.xy

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
                    # TODO: 如何科学判定？
                    return True
                else: # len == 1
                    field = currentFields[0]
                    if isinstance(field, (EmptyField, WaterField) ):
                        continue
                    elif not isinstance(field, TankField): # 说明这个方向上没有敌人
                        break
                    elif field.side != tank.side: # 遇到了敌人，准备射击
                        return True
                    else: # 遇到了队友
                        break
        return False


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
                    elif field.side != tank.side: # 遇到了敌人，准备射击
                        enemies.append(field)
                    else: # 遇到了队友
                        break

        return enemies


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
        oppBase = map_.bases[1 - tank.side]
        x1, y1 = tank.xy
        x2, y2 = oppTank.xy
        actions = []
        for dx, dy in get_searching_directions(x1, y1, oppBase.x, oppBase.y): # 优先逃跑向对方基地
            x3 = x1 + dx
            y3 = y1 + dy
            if x3 == x2 or y3 == y2: # 逃跑方向不对
                continue
            action = Action.get_action(x1, y1, x3, y3)
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

    def move_to(self, oppTank):
        """
        返回 self -> oppTank 的移动

        Input:
            enemy   TankField/BattleTank    所有带坐标的 tank 对象
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


    def is_face_to_enemy_base(self):
        """
        是否直面对方基地，没有任何障碍阻挡，用于特殊决策！
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
                    elif field is oppBase:
                        return True
                    else:
                        break
        return False


    def get_enemy_behind_brick(self, action):
        """
        返回相应行为的方向后的围墙后的敌人

        仅仅对应于 坦克|土墙|坦克  的相邻情况

        Input:
            - action   int   移动/射击行为，确定方向

        Return:
            - tank    TankField/None    敌人对应的 tank 对象，多个敌人只返回一个
                                        情况不符则返回 None
        """
        tank = self._tank
        map_ = self._map

        x1, y1 = tank
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action % 4]

        # 墙的位置
        x2 = x1 + dx
        y2 = y1 + dy

        # 墙后的位置
        x3 = x2 + dx
        x3 = y2 + dy

        if not map_.in_map(x2, y2) or not map_.in_map(x3, y3):
            return None

        fields2 = map_[x2, y2]
        if len(fields2) == 0:
            return None
        elif len(fields2) > 1:
            return None
        else:
            field = fields2[0]
            if isinstance(field, BrickField):
                pass
            else:
                return None

        fields3 = map_[x3, y3]
        if len(fields3) == 0:
            return None
        elif len(fields3) > 1:
            return fields3[0]
        else:
            field = fields3[0]
            if isinstance(field, TankField) and fiele.side != tank.side:
                return field
            else:
                return None

        return None

    def get_nearest_enemy(self, block_teammate=False):
        """
        获得最近的敌人，移动距离

        Return:
            - enemy   TankField
        """
        tank = self._tank
        map_ = self._map

        _enemies = map_.tanks[1 - tank.side]
        enemies = [ enemy for enemy in _enemies if not enemy.destroyed ] # 已经被摧毁的敌人就不考虑了

        if len(enemies) == 0: # 胜利？
            return None
        if len(enemies) < 2:
            return enemies[0]

        routes = [ self.get_route_to_enemy_by_movement(enemy) for enemy in enemies ]
        routesLen = [ get_route_length(route) for route in routes ]

        if all( length == INFINITY_ROUTE_LENGTH for length in routesLen ): # 均不可到达？
            routes = [ self.get_route_to_enemy_by_movement(enemy, block_teammate=False)
                            for enemy in enemies ] # 因为队友阻塞 ?
            routesLen = [ get_route_length(route) for route in routes ]

        routeLenWithEnemyList = [
            (length, enemy) for length, enemy in zip(routesLen, enemies)
                    if length != INFINITY_ROUTE_LENGTH # 队友阻塞导致 -1 需要去掉
        ]
        # debug_print(routeLenWithEnemyList)

        idx = routeLenWithEnemyList.index(
                    min(routeLenWithEnemyList, key=lambda tup: tup[0]) )

        return enemies[idx]


    def check_is_outer_wall_of_enemy_base(self, field, layer=1):
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