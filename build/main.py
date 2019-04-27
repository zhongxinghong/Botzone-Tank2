# -*- coding: utf-8 -*-
# @Author:   Rabbit
# @Filename: main.py
# @Date:     2019-04-27 19:09:17
# @Description: Auto-built single-file Python script for Botzone/Tank2


#{ BEGIN 'const.py' }#

#-----------------#
# Release Version #
#-----------------#
DEBUG_MODE        = False
LONG_RUNNING_MODE = False

#-------------#
# Game Config #
#-------------#
MAP_HEIGHT     = 9
MAP_WIDTH      = 9
SIDE_COUNT     = 2
TANKS_PER_SIDE = 2

#-------------#
# Game Status #
#-------------#
GAME_STATUS_NOT_OVER = -2
GAME_STATUS_DRAW     = -1
GAME_STATUS_BLUE_WIN = 0
GAME_STATUS_RED_WIN  = 1


DIRECTIONS_UDLR = ( (0,-1), (0,1), (-1,0), (1,0) ) # 上下左右

#{ END 'const.py' }#



#{ BEGIN 'const.py' }#

#-----------------#
# Release Version #
#-----------------#
DEBUG_MODE        = False
LONG_RUNNING_MODE = False

#-------------#
# Game Config #
#-------------#
MAP_HEIGHT     = 9
MAP_WIDTH      = 9
SIDE_COUNT     = 2
TANKS_PER_SIDE = 2

#-------------#
# Game Status #
#-------------#
GAME_STATUS_NOT_OVER = -2
GAME_STATUS_DRAW     = -1
GAME_STATUS_BLUE_WIN = 0
GAME_STATUS_RED_WIN  = 1


DIRECTIONS_UDLR = ( (0,-1), (0,1), (-1,0), (1,0) ) # 上下左右

#{ END 'const.py' }#



#{ BEGIN 'global_.py' }#

import time
import sys
import json
import random
import numpy as np
from collections import deque
from pprint import pprint
import functools

#{ END 'global_.py' }#



#{ BEGIN 'utils.py' }#

if DEBUG_MODE:
    debug_print  = print
    debug_pprint = pprint
else:
    debug_print  = lambda *args, **kwargs: None
    debug_pprint = debug_print


class _Missing(object):
    """
    from werkzeug._internal
    """

    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_MISSING = _Missing()


class CachedProperty(property):
    """
    from werkzeug.utils
    """

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _MISSING)
        if value is _MISSING:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

    @staticmethod
    def clean(obj, key):
        """
        清除缓存
        """
        obj.__dict__.pop(key, None)


class Singleton(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(Singleton, cls).__call__(*args)
        return cls._instance[cls]

#{ END 'utils.py' }#



#{ BEGIN 'action.py' }#

class Action(object):

    DUMMY       = -3
    INVALID     = -2
    STAY        = -1
    MOVE_UP     = 0
    MOVE_RIGHT  = 1
    MOVE_DOWN   = 2
    MOVE_LEFT   = 3
    SHOOT_UP    = 4
    SHOOT_RIGHT = 5
    SHOOT_DOWN  = 6
    SHOOT_LEFT  = 7

    # 根据 action 的值判断移动方向和射击方向
    DIRECTION_OF_ACTION_X  = (  0, 1, 0, -1 )
    DIRECTION_OF_ACTION_Y  = ( -1, 0, 1,  0 )

    @staticmethod
    def is_move(action):
        """
        是否为移动行动
        """
        return 0 <= action <= 3

    @staticmethod
    def is_shoot(action):
        """
        是否为射击行动
        """
        return 4 <= action <= 7

    @staticmethod
    def is_opposite(action1, action2):
        """
        两个行动方向是否相对

        注： 此处不检查两个行为是否均与方向有关，即均处于 [0, 7] 范围内
        """
        return action1 % 4 == (action2 + 2) % 4

    @staticmethod
    def get_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的 move 行为值
        """
        dx = x2 - x1
        dy = y2 - y1

        if dx == dy == 0:
            return __class__.STAY

        for idx, dxy in enumerate(zip(__class__.DIRECTION_OF_ACTION_X,
                                      __class__.DIRECTION_OF_ACTION_Y)):
            if (dx, dy) == dxy:
                return idx
        else:
            raise Exception("can't move from (%s, %s) to (%s, %s) in one step"
                             % (x1, y1, x2, y2) )

#{ END 'action.py' }#



#{ BEGIN 'field.py' }#

class Field(object):


    DUMMY     = -1
    EMPTY     = 0
    BRICK     = 1
    STEEL     = 2
    WATER     = 3

    #-----------------------#
    # rule: BASE + 1 + side #
    #-----------------------#
    BASE      = 4 # side = -1
    BLUE_BASE = 5 # side = 0
    RED_BASE  = 6 # side = 1

    #-----------------------#
    # rule: TANK + 1 + side #
    #-----------------------#
    TANK      = 7 # side = -1
    BLUE_TANK = 8 # side = 0
    RED_TANK  = 9 # side = 1


    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.destroyed = False

    @property
    def coordinate(self):
        return (self.x, self.y)

    @property
    def xy(self):
        return (self.x, self.y)

    @property
    def yx(self):
        return (self.y, self.x)

    def __repr__(self):
        return "%s(%d, %d)" % (
            self.__class__.__name__, self.x, self.y)


class EmptyField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.EMPTY)


class BrickField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.BRICK)


class SteelField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.STEEL)


class WaterField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.WATER)


class BaseField(Field):

    def __init__(self, x, y, side):
        super().__init__(x, y, Field.BASE)
        self._side = side

    @property
    def side(self):
        return self._side

    def __repr__(self):
        return "%s(%d, %d, side: %d)" % (
            self.__class__.__name__, self.x, self.y, self._side)


class TankField(Field):

    def __init__(self, x, y, side, id):
        super().__init__(x, y, Field.TANK)
        self._side = side
        self._id = id
        self.previousAction = Action.DUMMY

    @property
    def side(self):
        return self._side

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return "%s(%d, %d, side: %d, id: %d)" % (
            self.__class__.__name__, self.x, self.y, self._side, self._id)

#{ END 'field.py' }#



#{ BEGIN 'map_.py' }#

class Map(object):

    def __init__(self, width, height):
        self._width = width
        self._height = height

        self._content = [
            [[] for x in range(width)] for y in range(height)
        ]

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def size(self):
        return (self._width, self._height)


class Tank2Map(Map, metaclass=Singleton):

    def __init__(self, width, height):
        super().__init__(width, height)
        self._tanks = [ [ None for _ in range(TANKS_PER_SIDE) ] for __ in range(SIDE_COUNT) ]
        self._bases = [ None for _ in range(SIDE_COUNT) ]
        self._init_bases()
        self._init_tanks()


    @property
    def tanks(self):
        return self._tanks

    @CachedProperty
    def matrix(self):
        """
        缓存 to_type_matrix 的值

        WARNING:

            - 因为 list 是可变对象，因此不要对返回值进行修改，以免缓存的属性值改变
            - 如需修改，需要首先调用 np.copy(matrix) 获得一个副本，然后对副本进行修改
        """
        return self.to_type_matrix()

    @CachedProperty
    def matrix_T(self):
        """
        转置后的 matrix 属性
        """
        return self.matrix.T


    def _init_bases(self):
        """
        初始化基地和基地前的钢墙
        """
        assert self._width % 2 == 1, "Map width must be odd"
        xc = self._width // 2 # x-center
        y1 = 0
        y2 = self._height - 1

        basePoints = [
            (xc, y1), # side 1 蓝方
            (xc, y2), # side 2 红方
        ]
        for side, (x, y) in enumerate(basePoints):
            base = self.create_base_field(x, y, side)
            self._bases[side] = base

    def _init_tanks(self):
        """
        初始化坦克
        """
        x1, x2 = (2, 6)
        y1, y2 = (0, self._height-1)
        tankPoints = [
            [ (x1, y1), (x2, y1) ], # side 1 蓝方  左 0 右 1
            [ (x2, y2), (x1, y2) ], # side 2 红方  左 1 右 0
        ]
        for side, points in enumerate(tankPoints):
            tanks = self._tanks[side]
            for idx, (x, y) in enumerate(points):
                tank = self.create_tank_field(x, y, side, idx)
                tanks[idx] = tank

    def reset(self):
        """
        重置地图
        """
        CachedProperty.clean(self, "matrix")   # 务必清空缓存
        CachedProperty.clean(self, "matrix_T")
        width, height = self.size
        self.__init__(width, height)


    def insert_field(self, field):
        x, y = field.xy
        self._content[y][x].append(field)
        field.destroyed = False

    def remove_field(self, field):
        x, y = field.xy
        self._content[y][x].remove(field)
        field.destroyed = True

    def create_empty_field(self, x, y):
        field = EmptyField(x, y)
        self.insert_field(field)
        return field

    def create_brick_field(self, x, y):
        field = BrickField(x, y)
        self.insert_field(field)
        return field

    def create_steel_field(self, x, y):
        field = SteelField(x, y)
        self.insert_field(field)
        return field

    def create_water_field(self, x, y):
        field = WaterField(x, y)
        self.insert_field(field)
        return field

    def create_base_field(self, x, y, side):
        field = BaseField(x, y, side)
        self.insert_field(field)
        return field

    def create_tank_field(self, x, y, side, id):
        field = TankField(x, y, side, id)
        self.insert_field(field)
        return field


    def get_fields(self, x, y):
        """
        获得 (x, y) 坐标下的 fields
        """
        if not self.in_map(x, y):
            raise Exception("(%s, %s) is not in map" % (x, y) )
        return self._content[y][x]

    def to_type_matrix(self):
        """
        转化成以 field.type 值表示的地图矩阵

        Return:
            - matrix   np.array( [[int]] )   二维的 type 值矩阵

        WARNING:
            - 矩阵的索引方法为 (y, x) ，实际使用时通常需要转置一下，使用 matrix.T
        """
        width, height = self.size
        matrix = [ [ Field.DUMMY for x in range(width) ] for y in range(height) ]

        for y in range(height):
            for x in range(width):
                fields = self._content[y][x]
                if len(fields) == 0:
                    matrix[y][x] = Field.EMPTY
                elif len(fields) > 2:
                    matrix[y][x] = Field.TANK # 重合视为一个坦克
                else:
                    field = fields[0]
                    if isinstance(field, (BaseField, TankField) ):
                        matrix[y][x] = field.type + 1 + field.side # 遵循 Field 中常数定义的算法
                    else:
                        matrix[y][x] = field.type

        return np.array(matrix)

    def in_map(self, x, y):
        """
        判断 (x, y) 坐标是否位于地图内
        """
        return 0 <= x < self._width and 0 <= y < self._height

    def is_valid_move_action(self, tank, action):
        """
        判断是否为合法的移动行为
        """
        assert Action.is_move(action), "action %s is not a move-action" % action
        _dx = Action.DIRECTION_OF_ACTION_X
        _dy = Action.DIRECTION_OF_ACTION_Y
        _TYPE_CAN_MOVE_TO = ( Field.EMPTY, Field.DUMMY )
        x, y = tank.xy
        x += _dx[action]
        y += _dy[action]
        if not self.in_map(x, y):
            return False
        fields = self._content[y][x]
        if len(fields) == 0:
            return True
        elif len(fields) == 1:
            _type = fields[0].type
            if _type in _TYPE_CAN_MOVE_TO:
                return True
        return False

    def is_valid_shoot_action(self, tank, action):
        """
        判断是否为合法的设计行为
        """
        debug_print(tank.__dict__)
        debug_print(tank.previousAction)
        assert Action.is_shoot(action), "action %s is not a shoot-action" % action
        return not Action.is_shoot(tank.previousAction) # 只要不连续两回合射击都合理

    def is_valid_action(self, tank, action):
        """
        判断是否为合法行为
        """
        debug_print("validate action, tank: %s, action: %s" % (tank, action) )
        if action == Action.INVALID:
            return False
        elif action == Action.STAY:
            return True
        elif Action.is_move(action):
            return self.is_valid_move_action(tank, action)
        elif Action.is_shoot(action):
            return self.is_valid_shoot_action(tank, action)
        else: # 未知的行为
            raise Exception("unexpected action %s" % action)


    def get_destroyed_fields(self, tank, action):
        """
        下一回合某坦克执行一个射击行为后，将会摧毁的 fields

        用于单向分析 action 所能造成的影响，不考虑对方下一回合的决策

        - 不判断自身是否与其他 tank 重叠
        - 如果对方是 tank 认为对方下回合不开炮

        Return:
            - fields   [Field]/[]   被摧毁的 fields
                                    如果没有对象被摧毁，则返回空列表
        """
        assert self.is_valid_shoot_action(tank, action)
        x, y = tank.xy

        _dx = Action.DIRECTION_OF_ACTION_X
        _dy = Action.DIRECTION_OF_ACTION_Y

        action %= 4 # 使之与 dx, dy 的 idx 对应

        while True: # 查找该行/列上是否有可以被摧毁的对象

            x += _dx[action]
            y += _dy[action]

            if not self.in_map(x, y):
                break

            currentFields = self._content[y][x]

            if len(currentFields) == 0: # 没有对象
                continue
            elif len(currentFields) > 1: # 均为坦克
                return currentFields
            else: # len == 1
                field = currentFields[0]
                if isinstance(field, EmptyField): # 空对象
                    continue
                elif isinstance(field, WaterField): # 忽视水路
                    continue
                elif isinstance(field, SteelField): # 钢墙不可摧毁
                    return []
                else:
                    return currentFields

        return [] # 没有任何对象被摧毁


    def do_actions(self, my_side, my_actions, opposite_actions):
        """
        在地图上执行两方的行为
        """
        assert len(my_actions) ==  len(opposite_actions)

        _currentTurn = 0

        for aMyActions, anOppositeActions in zip(my_actions, opposite_actions):

            _currentTurn += 1

            if DEBUG_MODE:
                print("Start Turn: %s" % _currentTurn)
                self.print_out()

            _actions = [ None for _ in range(SIDE_COUNT) ]

            mySide  = my_side
            oppSide = 1 - my_side

            _actions[mySide]  = aMyActions
            _actions[oppSide] = anOppositeActions

            # 检查 actions 合理性
            for tanks in self._tanks:
                for tank in tanks:
                    action = _actions[tank.side][tank.id]
                    if not self.is_valid_action(tank, action):
                        print(tank.type, tank.id, action)
                        self.print_out()
                        raise Exception("Invalid action %s" % action)

            _dx = Action.DIRECTION_OF_ACTION_X
            _dy = Action.DIRECTION_OF_ACTION_Y

            # 处理停止和移动
            for tanks in self._tanks:
                for tank in tanks:
                    action = _actions[tank.side][tank.id]
                    if action == Action.STAY:
                        tank.previousAction = action # 缓存本次停止行为
                    if ( not tank.destroyed
                         and Action.is_move(action)
                        ):
                        tank.previousAction = action # 缓存本次移动行动
                        self.remove_field(tank)
                        tank.x += _dx[action]
                        tank.y += _dy[action]
                        self.insert_field(tank)

            fieldsToBeDestroyed = set()

            for tanks in self._tanks:
                for tank in tanks:

                    action = _actions[tank.side][tank.id]

                    if not tank.destroyed and Action.is_shoot(action):
                        tank.previousAction = action # 缓存本次射击行动

                        x, y = tank.xy
                        action %= 4 # 使之与 dx, dy 的 idx 对应

                        hasMultiTankWithMe = ( len( self._content[y][x] ) > 1 )

                        while True:
                            # 查找该行/列上是否有可以被摧毁的对象
                            x += _dx[action]
                            y += _dy[action]
                            if not self.in_map(x, y):
                                break
                            currentFields = self._content[y][x]

                            if len(currentFields) > 0:

                                if len(currentFields) == 1: # 如果 > 1 则必定都是坦克
                                    field = currentFields[0]

                                    # 水路判断
                                    if isinstance(field, WaterField):
                                        continue # 忽视水路

                                    # 对射判断
                                    if ( not hasMultiTankWithMe
                                         and isinstance(field, TankField)
                                        ): # 此时两方所在格子均都只有一架坦克
                                        oppTank = field
                                        oppAction = _actions[oppTank.side][oppTank.id]
                                        if ( Action.is_shoot(oppAction)
                                             and Action.is_opposite(action, oppAction)
                                            ):
                                            break # 对射抵消

                                fieldsToBeDestroyed.update(currentFields)
                                break # 摧毁了第一个遇到的 field

            for field in fieldsToBeDestroyed:
                if not isinstance(field, SteelField):
                    self.remove_field(field)

            if DEBUG_MODE:
                print("End Turn: %s" % _currentTurn)
                self.print_out()


    def get_game_result(self):
        """
        判断胜利方

        Return:
            - result   int   比赛结果

                > GAME_STATUS_NOT_OVER   比赛尚未结束
                > GAME_STATUS_DRAW       平局
                > GAME_STATUS_BLUE_WIN   蓝方获胜
                > GAME_STATUS_RED_WIN    红方获胜
        """
        failed = [ False for _ in range(SIDE_COUNT) ] # 0 蓝方 1 红方

        for side in range(SIDE_COUNT):

            # 坦克全部被消灭
            tanks = self._tanks[side]
            if all(tank.destroyed for tank in tanks):
                failed[side] = True

            # 基地被摧毁
            baes = self._bases[base]
            if base.destroyed:
                failed[side] = True

        if failed[0] and failed[1]:
            return GAME_STATUS_DRAW
        elif not failed[0] and failed[1]:
            return GAME_STATUS_BLUE_WIN
        elif failed[0] and not failed[1]:
            return GAME_STATUS_RED_WIN
        else:
            return GAME_STATUS_NOT_OVER


    def print_out(self, compact=False):
        """
        [DEBUG] 输出整个地图

        Input:
            - compact   bool   是否以紧凑的形式输出
        """
        EMPTY_SYMBOL      = "　"
        BASE_SYMBOL       = "基"
        BRICK_SYMBOL      = "土"
        STEEL_SYMBOL      = "钢"
        WATER_SYMBOL      = "水"
        BLUE_TANK_SYMBOL  = "蓝"
        RED_TANK_SYMBOL   = "红"
        MULTI_TANK_SYMBOL = "重"
        UNEXPECTED_SYMBOL = "？"

        SPACE = "　" if not compact else ""

        _TEXT_WIDTH = (self._width * 2 - 1) if not compact else self._width
        CUT_OFF_RULE = "＝" * _TEXT_WIDTH

        print_inline = functools.partial(print, end=SPACE)

        print("\n%s" % CUT_OFF_RULE)
        if not compact:
            print("")
        for y in range(self._height):
            for x in range(self._width):
                fields = self._content[y][x]
                if len(fields) == 0:
                    print_inline(EMPTY_SYMBOL)
                elif len(fields) > 1:
                    print_inline(MULTI_TANK_SYMBOL)
                elif len(fields) == 1:
                    field = fields[0]
                    if isinstance(field, EmptyField):
                        print_inline(EMPTY_SYMBOL)
                    elif isinstance(field, BaseField):
                        print_inline(BASE_SYMBOL)
                    elif isinstance(field, BrickField):
                        print_inline(BRICK_SYMBOL)
                    elif isinstance(field, SteelField):
                        print_inline(STEEL_SYMBOL)
                    elif isinstance(field, WaterField):
                        print_inline(WATER_SYMBOL)
                    elif isinstance(field, TankField):
                        tank = field
                        if tank.side == 0:
                            print_inline(BLUE_TANK_SYMBOL)
                        elif tank.side == 1:
                            print_inline(RED_TANK_SYMBOL)
                        else:
                            print_inline(UNEXPECTED_SYMBOL)
                    else:
                        print_inline(UNEXPECTED_SYMBOL)
                else:
                    print_inline(UNEXPECTED_SYMBOL)
            print("\n" if not compact else "")
        print("%s\n" % CUT_OFF_RULE)

#{ END 'map_.py' }#



#{ BEGIN 'strategy/_utils.py' }#

def _find_shortest_route(start, end, matrix_T, side=-1,
                         cannot_reach_type=[Field.STEEL, Field.WATER]):
    """
    BFS 寻找最短路径

    Input:
        - start     (int, int)           起始坐标 (x1, y2)
        - end       (int, int)           终点坐标 (x2, y2)
        - matrix_T  np.array( [[int]] )  游戏地图的类型矩阵的转置
        - side      int                  游戏方，默认为 -1，该值会影响对 base 是否可到达的判断
                                         如果为本方基地，则不可到达，如果为对方基地，则可以到达

        - cannot_reach_type   [int]      除了基地以外，其他不可以到达的 field 类型

    Return:
        - route   [(int, int)]  包含 start 和 end 的从 start -> end
                                的最短路径，坐标形式 (x, y)
    """
    matrix = matrix_T
    x1, y1 = start
    x2, y2 = end

    matrixCanReach = (matrix != Field.BASE + 1 + side) # BASE, 遵守 Field 中常数的定义规则
    for t in cannot_reach_type:
        matrixCanReach &= (matrix != t)

    # struct Node:
    # [
    #     "xy":     (int, int)     目标节点
    #     "parent": Node or None   父节点
    # ]
    startNode = [ (x1, y1), None ]
    endNode   = [ (x2, y2), None ]    # 找到终点后设置 endNode 的父节点
    tailNode  = [ (-1, -1), endNode ] # endNode 后的节点

    queue = deque() # deque( [Node] )
    marked = np.zeros_like(matrix, dtype=np.bool8)

    width, height = matrix.shape # width, height 对应着转置前的 宽高

    def _in_matrix(x, y):
        return 0 <= x < width and 0 <= y < height

    def _enqueue_UDLR(node):
        for dx, dy in DIRECTIONS_UDLR:
            x, y = node[0]
            x3 = x + dx
            y3 = y + dy
            if not _in_matrix(x3, y3) or not matrixCanReach[x3, y3]:
                continue
            nextNode = [ (x3, y3), node ]
            queue.append(nextNode)


    _enqueue_UDLR(startNode)

    while len(queue) > 1:
        node = queue.popleft()
        x, y = node[0]

        if marked[x, y]:
            continue
        marked[x, y] = True

        if x == x2 and y == y2:  # 此时 node.xy == endNode.xy
            endNode[1] = node[1]
            break

        _enqueue_UDLR(node)


    route = []

    node = tailNode
    while True:
        node = node[1]
        if node is not None:
            route.append(node[0])
        else:
            break

    route.reverse()
    return route

#{ END 'strategy/_utils.py' }#



#{ BEGIN 'strategy/abstract.py' }#

class Strategy(object):

    def __init__(self, tank, map, **kwargs):
        """
        Input:
            - tank   TankField   需要做出决策的 tank
            - map    Tank2Map    当前地图
        """
        self._tank = tank
        self._map = map

    def make_decision(self):
        """
        做出决策

        Return:
            - action   int   Action 类中定义的动作编号
        """
        raise NotImplementedError

#{ END 'strategy/abstract.py' }#



#{ BEGIN 'strategy/random_action.py' }#

class RandomActionStrategy(Strategy):

    def make_decision(self):

        tank = self._tank
        map_ = self._map
        debug_print("RandomAction decision, tank %s" % tank)

        availableActions = []

        for action in range(Action.STAY, Action.SHOOT_LEFT + 1):

            if not map_.is_valid_action(tank, action):
                continue
            elif Action.is_shoot(action):
                destroyedFields = map_.get_destroyed_fields(tank, action)
                debug_print("Destroyed Fields:", destroyedFields)
                if len(destroyedFields) == 1:
                    field = destroyedFields[0]
                    if isinstance(field, BaseField) and field.side == tank.side:
                        continue # 保证不摧毁己方的基地
                    elif isinstance(field, TankField) and field.side == tank.side:
                        continue # 保证不摧毁队友，不过需要队友和敌人不重合

            availableActions.append(action)

        debug_print("Available actions: %s\n" % availableActions)
        return random.choice(availableActions)

#{ END 'strategy/random_action.py' }#



#{ BEGIN 'strategy/move_to_water.py' }#

class MoveToWaterStrategy(Strategy):

    def __init__(self, tank, map, water_points=None):
        """
        可以传入 water_points 的坐标，避免多次计算
        """
        super().__init__(tank, map)
        self._waterPoints = water_points


    @staticmethod
    def find_water_points(map):
        return np.argwhere(map.matrix_T == Field.WATER) # 转置为 xy 矩阵


    def make_decision(self):

        if self._waterPoints is None:
            self._waterPoints = self.find_water_points(self._map)

        tank        = self._tank
        map_        = self._map
        matrix_T    = map_.matrix_T
        waterPoints = self._waterPoints

        _dx = Action.DIRECTION_OF_ACTION_X
        _dy = Action.DIRECTION_OF_ACTION_Y


        xy = np.array( tank.xy )
        _idx = np.square( xy - waterPoints ).sum(axis=1).argmin()
        x2, y2 = nearestWaterPoint = waterPoints[_idx]

        route = _find_shortest_route(
                    tank.xy,
                    nearestWaterPoint,
                    matrix_T,
                    cannot_reach_type=[Field.STEEL] ) # 水域允许到达

        if DEBUG_MODE:
            map_.print_out()
            pprint(self._map.matrix)
            print("")
            pprint(route)

        x1, y1 = tank.xy
        if len(route) == 0:
            raise Exception("can't reach (%s, %s)" % (x2, y2) )

        if len(route) == 1: # 说明 start 和 end 相同
            x3, y3 = nextPoint = route[0] # 返回 start/end
        else:
            x3, y3 = nextPoint = route[1] # 跳过 start

        action = Action.get_action(x1, y1, x3, y3) # 必定是 move-action

        if not map_.is_valid_move_action(tank, action): # 墙或水
            x, y = tank.xy
            x += _dx[action]
            y += _dy[action]
            fields = map_.get_fields(x, y)
            assert len(fields) > 0, "except WATER or BRICK in (%s, %s)" % (x, y)
            field = fields[0]
            action += 4 # 尝试射击
            if not isinstance(field, WaterField): # 说明是墙
                pass # 射击一定成功，因为若上回合射击，这回合必定不会碰到墙
            else: # 是水面
                if map_.is_valid_shoot_action(tank, action): # 判断上回合是否射击
                    pass
                else: # 射击行为也不合法
                    action = Action.STAY # 如果游戏正常，则会停下，否则一开始会认为是合法，并继续移动

        return action

#{ END 'strategy/move_to_water.py' }#



#{ BEGIN 'stream.py' }#

class BotzoneIstream(object):

    def read(self):
        return input()


class BotzoneOstream(object):

    def write(self, data):
        print(data)

#{ END 'stream.py' }#



#{ BEGIN 'botzone.py' }#

class Botzone(object):

    def __init__(self, long_running):
        self._longRunning = long_running
        self._data = None
        self._globalData = None
        self._requests = []  # 对方的决策
        self._responses = [] # 己方的决策


    def handle_input(self, stream):
        """
        解析输入信息

        Input:
            - stream   TextIOWrapper   输入流对象，必须实现 read 方法
        """
        inputJSON = json.loads(stream.read())

        self._requests   = inputJSON["requests"]
        self._responses  = inputJSON["responses"]
        self._data       = inputJSON.get("data", None)
        self._globalData = inputJSON.get("globaldata", None)

    def make_output(self, stream, response, debug, data, globaldata):
        """
        输出结果

        Input：
            - stream       TextIOWrapper   输出流对象，必须实现 write 方法
            - response     dict            Bot 此回合的输出信息
            - debug        dict/str        调试信息，将被写入log，最大长度为1KB
            - data         dict            Bot 此回合的保存信息，将在下回合输入
            - globaldata   dict            Bot 的全局保存信息，将会在下回合输入，
                                           对局结束后也会保留，下次对局可以继续利用
        """
        stream.write(json.dumps({
            "response": response,
            "debug": debug,
            "data": data,
            "globaldata": globaldata,
            }))

        if not self._longRunning:
            sys.exit(0)



class Tank2Botzone(Botzone, metaclass=Singleton):

    def __init__(self, map, long_running=False):
        super().__init__(long_running)
        self._mySide = -1
        self._map = map


    @property
    def mySide(self):
        return self._mySide


    def _parse_field_points(self, binary):
        """
        解析 requests 中存在有某种类型 field 的坐标

        Input:
            - binary   list   某种类型 field 的 binary 标记
        Yield:
            - (x, y)   tuple(int, int)   这个坐标上存在该类型 field
        """
        _MAP_WIDTH = self._map.width
        for i in range(3):
            mask = 1
            for y in range(i * 3, i * 3 + 3):
                for x in range(_MAP_WIDTH):
                    if binary[i] & mask:
                        yield (x, y)
                    mask <<= 1

    def handle_input(self, stream=sys.stdin):

        super().handle_input(stream)

        header = self._requests.pop(0) # 此时 header 被去掉

        self._mySide = header["mySide"]

        for x, y in self._parse_field_points(header["brickfield"]):
            self._map.create_brick_field(x, y)

        for x, y in self._parse_field_points(header["steelfield"]):
            self._map.create_steel_field(x, y)

        for x, y in self._parse_field_points(header["waterfield"]):
            self._map.create_water_field(x, y)

        self._map.do_actions(self._mySide, self._responses, self._requests)


    def make_output(self, actions, stream=sys.stdout,
                    debug=None, data=None, globaldata=None):
        super().make_output(stream, actions, debug, data, globaldata)

#{ END 'botzone.py' }#



#{ BEGIN 'main.py' }#

if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_, long_running=LONG_RUNNING_MODE)

    istream = BotzoneIstream()
    ostream = BotzoneOstream()

    while True:

        t1 = time.time()

        if LONG_RUNNING_MODE: # 这个模式下 map 对象会复用，首先需要重置
            map_.reset()

        terminal.handle_input(stream=istream)

        side = terminal.mySide
        tanks = map_.tanks[side]

        '''waterPoints = MoveToWaterStrategy.find_water_points(map_)

        actions = []
        for tank in tanks:
            s = MoveToWaterStrategy(tank, map_, waterPoints)
            action = s.make_decision()
            actions.append(action)'''

        actions = []
        for tank in tanks:
            s = RandomActionStrategy(tank, map_)
            action = s.make_decision()
            actions.append(action)

        t2 = time.time()

        debugInfo = {
            "cost": round(t2 - t1, 3)
            }

        terminal.make_output(actions, stream=ostream, debug=debugInfo)

#{ END 'main.py' }#



