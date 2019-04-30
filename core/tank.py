# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 03:01:59
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 00:23:46
"""
采用装饰器模式，对 TankField 进行包装，使之具有判断战场形势的能力

"""

__all__ = [

    "BattleTank",

    ]

from .const import DIRECTIONS_URDL
from .utils import CachedProperty, debug_print
from .action import Action
from .field import Field, SteelField, TankField, EmptyField, WaterField, BaseField
from .strategy.utils import fake_map_matrix_T_without_enemy
from .strategy.bfs import find_shortest_route_for_shoot, find_shortest_route_for_move,\
                        get_route_length, DEFAULT_BLOCK_TYPES, DEFAULT_DESTROYABLE_TYPES

#{ BEGIN }#

class BattleTank(object):

    __instances = {} # { (side, id): instance }

    def __new__(cls, tank, map, *args, **kwargs):
        """
        以 (side, id) 为主键，缓存已经创建过的作战对象
        使得该对象对于特定的 tank 对象为 Singleton
        """
        key = (tank.side, tank.id)
        obj = __class__.__instances.get(key)
        if obj is None:
            obj = super(BattleTank, cls).__new__(cls, *args, **kwargs)
            __class__.__instances[key] = obj
            ## BattleTank.__init__(obj, tank, map) # 在此处初始化
            obj._tank = tank
            obj._map = map
            obj._aggressive = False
            obj.__attackingRoute = None
            ## END BattleTank.__init__
        return obj

    def __init__(self, tank, map):
        '''self._tank = tank
        self._map = map
        self._aggressive = False # 是否具有侵略性
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
    def aggressive(self):
        return self._aggressive

    @property
    def defensive(self):
        return not self._aggressive

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

        if len(route) == 0: # 没有找到路线，这种情况不可能
            return Action.STAY
        elif len(route) == 1:    # 说明 start 和 end 相同，已经到达基地，这种情况也不可能
            return Action.STAY # 停留不动

        x1, y1 = tank.xy
        x3, y3, _, _ = route[1] # 跳过 start
        action = Action.get_action(x1, y1, x3, y3) # move-action
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action]

        ## 优先移动 ##
        if map_.is_valid_move_action(tank, action):
            # 但是，如果正前方就是基地，则不移动，只射击
            for field in self.get_destroyed_fields_if_shoot(action):
                if isinstance(field, BaseField): # 如果敌人基地在前方
                    if self.canShoot: # 如果自己可以射击
                        return action + 4
                    else: # 不能射击，但是敌人基地就在眼前
                        # TODO: 可以考虑回避敌人的攻击，如果有的话？
                        return action
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
                        ))
        return route


    def get_route_to_enemy_by_movement(self, oppTank):
        """
        近身条件下，获得到达对方的路劲
        """
        tank = self._tank
        map_ = self._map
        side = tank.side
        route = find_shortest_route_for_move(
                            tank.xy,
                            oppTank.xy,
                            map_.matrix_T,
                            block_types=DEFAULT_BLOCK_TYPES+(
                                Field.BASE + 1 + side,
                                Field.TANK + 1 + side, # 不将对方 Tank 视为 block
                                Field.MULTI_TANK,
                            ))
        return route


    def has_enemy_around(self):
        """
        周围是否存在敌军
        """
        tank = self._tank
        map_ = self._map

        for dx, dy in DIRECTIONS_URDL:
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

        enemies = []

        for dx, dy in DIRECTIONS_URDL:
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
                        if instance(field, TankField) and field.side != tank.side:
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
        x1, y1 = tank.xy
        x2, y2 = oppTank.xy
        actions = []
        for dx, dy in DIRECTIONS_URDL:
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
        当前地形是否拥有闪避的机会，用来判断小路
        """
        tank = self._tank
        map_ = self._map
        x, y = self._tank.xy

        actions = []

        for dx, dy in DIRECTIONS_URDL:
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


    def shoot_to(self, oppTank):
        """
        返回 self -> oppTank 的射击行为

        Input:
            - oppTank   TankField/BattleTank    能够通过 x, y, xy 获取坐标值的坦克对象

        Return:
            - action   int
        """
        x1, y1 = self._tank.xy
        x2, y2 = oppTank.xy
        return Action.get_action(x1, y1, x2, y2) + 4 # move -> shoot !


    def get_destroyed_fields_if_shoot(self, action):
        """
        如果一个 move -> shoot 可以摧毁那些对象？

        用于 move 不安全而又不想白白等待的情况，尝试采用进攻开路

        Input:
            - action   int   原始的移动行为（事实上也可以是射击 ...）

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
#{ END }#