# -*- coding: utf-8 -*-
# @Author:   Rabbit
# @Filename: botzone_tank2.py
# @Date:     2019-05-01 02:46:26
# @Description: 
"""
MIT License

Copyright (c) 2019 Rabbit

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

#{ BEGIN 'const.py' }#

#----------------------#
# Environment Variable #
#----------------------#
DEBUG_MODE        = False
LONG_RUNNING_MODE = False
SIMULATOR_ENV     = False
COMPACT_MAP       = False
SIMULATOR_PRINT   = True

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

BLUE_SIDE = 0
RED_SIDE  = 1

DIRECTIONS_URDL = ( (0,-1), (1,0), (0,1), (-1,0) ) # 上右下左，与行为一致

#{ END 'const.py' }#



#{ BEGIN 'const.py' }#

#----------------------#
# Environment Variable #
#----------------------#
DEBUG_MODE        = False
LONG_RUNNING_MODE = False
SIMULATOR_ENV     = False
COMPACT_MAP       = False
SIMULATOR_PRINT   = True

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

BLUE_SIDE = 0
RED_SIDE  = 1

DIRECTIONS_URDL = ( (0,-1), (1,0), (0,1), (-1,0) ) # 上右下左，与行为一致

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

_null_func = lambda *args, **kwargs: None

if DEBUG_MODE:
    debug_print  = print
    debug_pprint = pprint
else:
    debug_print  = _null_func
    debug_pprint = _null_func

if SIMULATOR_ENV and SIMULATOR_PRINT:
    simulator_print  = print
    simulator_pprint = pprint
else:
    simulator_print  = _null_func
    simulator_pprint = _null_func


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

    # 空与无效
    DUMMY       = -3 # 额外添加的
    INVALID     = -2

    # 停止
    STAY        = -1

    # 移动
    MOVE_UP     = 0
    MOVE_RIGHT  = 1
    MOVE_DOWN   = 2
    MOVE_LEFT   = 3

    # 射击
    SHOOT_UP    = 4
    SHOOT_RIGHT = 5
    SHOOT_DOWN  = 6
    SHOOT_LEFT  = 7

    # 根据 action 的值判断移动方向和射击方向
    DIRECTION_OF_ACTION_X  = (  0, 1, 0, -1 )
    DIRECTION_OF_ACTION_Y  = ( -1, 0, 1,  0 )
    DIRECTION_OF_ACTION_XY = ( (0,-1), (1,0), (0,1), (-1,0) )

    _ACTION_NAMES = [
        "Invalid",  "Stay",
        "Up Move",  "Right Move",  "Down Move",  "Left Move",
        "Up Shoot", "Right Shoot", "Down Shoot", "Left Shoot",
    ]

    @staticmethod
    def is_valid(action): # 是否为有效行为
        return -2 < action <= 7

    @staticmethod
    def is_stay(action): # 是否为停止行为
        return action == -1

    @staticmethod
    def is_move(action): # 是否为移动行为
        return 0 <= action <= 3

    @staticmethod
    def is_shoot(action): # 是否为射击行为
        return 4 <= action <= 7

    @staticmethod
    def is_opposite(action1, action2):
        """
        两个行动方向是否相对
        """
        if action1 == -1 or action2 == -1:
            return False
        return action1 % 4 == (action2 + 2) % 4

    @staticmethod
    def is_same_direction(action1, action2):
        """
        两个行动方向是否相同
        """
        if action1 == -1 or action2 == -1:
            return False
        return action1 % 4 == action2 % 4

    @staticmethod
    def get_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的 move 行为值
        可以不相邻！
        """
        dx = np.sign(x2 - x1)
        dy = np.sign(y2 - y1)

        if dx == dy == 0:
            return -1 # STAY

        for idx, dxy in enumerate(__class__.DIRECTION_OF_ACTION_XY):
            if (dx, dy) == dxy:
                return idx
        else:
            raise Exception("can't move from (%s, %s) to (%s, %s) in one step"
                             % (x1, y1, x2, y2) )

    @staticmethod
    def get_name(action):
        return __class__._ACTION_NAMES[action + 2]

#{ END 'action.py' }#



#{ BEGIN 'field.py' }#

class Field(object):

    DUMMY      = -1
    EMPTY      = 0
    BRICK      = 1
    STEEL      = 2
    WATER      = 3

    #-----------------------#
    # rule: BASE + 1 + side #
    #-----------------------#
    BASE       = 4 # side = -1
    BLUE_BASE  = 5 # side = 0
    RED_BASE   = 6 # side = 1

    #-----------------------#
    # rule: TANK + 1 + side #
    #-----------------------#
    TANK       = 7 # side = -1
    BLUE_TANK  = 8 # side = 0
    RED_TANK   = 9 # side = 1

    MULTI_TANK = 10


    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.destroyed = False

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
        return "%s(%d, %d, %d)" % (
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
        return "%s(%d, %d, %d, %d)" % (
            self.__class__.__name__, self.x, self.y, self._side, self._id)


# const
BASE_FIELD_TYPES = ( Field.BASE, Field.BLUE_BASE, Field.RED_BASE )
TANK_FIELD_TYPES = ( Field.TANK, Field.BLUE_TANK, Field.RED_TANK, Field.MULTI_TANK )

#{ END 'field.py' }#



#{ BEGIN 'map_.py' }#

class Map(object):

    def __init__(self, width, height):
        self._width   = width
        self._height  = height
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

    def in_map(self, x, y):
        """
        判断 (x, y) 坐标是否位于地图内
        """
        return 0 <= x < self._width and 0 <= y < self._height

    def __getitem__(self, xy):
        """
        获得 xy: (x, y) 的内容
        """
        x, y = xy
        if not self.in_map(x, y):
            raise Exception("(%s, %s) is not in map" % (x, y) )
        return self._content[y][x]

    def get_fields(self, x, y):
        return self[x, y]


class Tank2Map(Map, metaclass=Singleton):

    def __init__(self, width, height):
        super().__init__(width, height)
        self._tanks = [ [ None for _ in range(TANKS_PER_SIDE) ] for __ in range(SIDE_COUNT) ]
        self._bases = [ None for _ in range(SIDE_COUNT) ]
        self._turn  = 0
        self._destroyedRecords = [] # Stack([Record]) 记录被摧毁的 fields 用于回滚
            # struct Record: (
            #   turn: int,
            #   xy: (int, int),
            #   field: Field,
            # )
        self._previousActions = [] # Stack([ [[int, int], [int, int]] ]) 所有坦克的历史动作记录，用于回滚
        self._init_bases()
        self._init_tanks()


    def reset(self): # 重置整个地图
        self.__clean_cache()
        width, height = self.size
        self.__init__(width, height)

    def __clean_cache(self): # 清除缓存属性
        CachedProperty.clean(self, "matrix")
        CachedProperty.clean(self, "matrix_T")

    @property
    def turn(self): # 当前回合数
        return self._turn

    @property
    def tanks(self):
        return self._tanks

    @property
    def bases(self):
        return self._bases

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
            base = BaseField(x, y, side)
            self._bases[side] = base
            self.insert_field(base)

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
                tank = TankField(x, y, side, idx)
                self.insert_field(tank)
                tanks[idx] = tank

    def insert_field(self, field):
        self[field.xy].append(field)
        field.destroyed = False

    def remove_field(self, field, record=True):
        self[field.xy].remove(field)
        field.destroyed = True
        if record: # 记录被清楚的对象
            r = ( self._turn, field.xy, field )
            self._destroyedRecords.append(r)

    def to_type_matrix(self):
        """
        转化成以 field.type 值表示的地图矩阵

        Return:
            - matrix   np.array( [[int]] )   二维的 type 值矩阵

        WARNING:
            - 矩阵的索引方法为 (y, x) ，实际使用时通常需要转置一下，使用 matrix.T
        """
        width, height = self.size
        matrix = np.full((height, width), Field.DUMMY, dtype=np.int8)
        for y in range(height):
            for x in range(width):
                fields = self.get_fields(x, y)
                if len(fields) == 0:
                    matrix[y, x] = Field.EMPTY
                elif len(fields) > 2:
                    matrix[y, x] = Field.MULTI_TANk # 重合视为一个坦克
                else:
                    field = fields[0]
                    if isinstance(field, (BaseField, TankField) ):
                        matrix[y, x] = field.type + 1 + field.side # 遵循 Field 中常数定义的算法
                    else:
                        matrix[y, x] = field.type
        return matrix

    def has_multi_tanks(self, x, y):
        """
        判断某坐标点是否有多辆坦克堆叠
        """
        return len( self.get_fields(x, y) ) > 1

    def is_valid_move_action(self, tank, action):
        """
        判断是否为合法的移动行为
        """
        assert Action.is_move(action), "action %s is not a move-action" % action

        _FIELDS_CAN_MOVE_TO = ( Field.DUMMY, Field.EMPTY ) # 遇到坦克不能移动！
        x, y = tank.xy
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action]
        x += dx
        y += dy
        if not self.in_map(x, y):
            return False
        fields = self.get_fields(x, y)
        if len(fields) == 0:
            return True
        elif len(fields) == 1:
            _type = fields[0].type
            if _type in _FIELDS_CAN_MOVE_TO:
                return True
        return False

    def is_valid_shoot_action(self, tank, action):
        """
        判断是否为合法的设计行为
        """
        assert Action.is_shoot(action), "action %s is not a shoot-action" % action
        return not Action.is_shoot(tank.previousAction) # 只要不连续两回合射击都合理

    def is_valid_action(self, tank, action):
        """
        判断是否为合法行为
        """
        if not Action.is_valid(action):
            return False
        elif Action.is_stay(action):
            return True
        elif Action.is_move(action):
            return self.is_valid_move_action(tank, action)
        elif Action.is_shoot(action):
            return self.is_valid_shoot_action(tank, action)
        else: # 未知的行为
            raise Exception("unexpected action %s" % action)


    def perform(self, blue_actions, red_actions):
        """
        执行一回合的行为

        Input:
            - blue_actions   [int, int]   蓝方 0, 1 号坦克将执行的动作
            - red_actions    [int, int]   红方 0, 1 号坦克将执行的动作
        """
        self._turn += 1
        self.__clean_cache()

        #debug_print("Start Turn: %s" % self._turn)
        #self.debug_print_out("")

        _dx = Action.DIRECTION_OF_ACTION_X
        _dy = Action.DIRECTION_OF_ACTION_Y

        _actions = [ blue_actions, red_actions ]
        _fieldsToBeDestroyed = set() # 使用 set 避免重复

        # 记录老的 previous actions
        _oldPreviousActions = [ [ tank.previousAction for tank in tanks ] for tanks in self._tanks ]
        self._previousActions.append(_oldPreviousActions) # 记录

        # 检查 actions 合理性，修改 tank 缓存
        for tanks in self._tanks:
            for tank in tanks:
                action = _actions[tank.side][tank.id]
                if not self.is_valid_action(tank, action):
                    raise Exception("%s will perform an invalid action %s"
                                     % (tank, action) )
                tank.previousAction = action # 缓存本次行为
                #simulator_print(tank.previousAction)
                #debug_print(tank, action)
        #debug_print()
        #simulator_print("perform turn: ", self._turn, self._previousActions[-1])


        # 处理停止和移动
        for tanks in self._tanks:
            for tank in tanks:
                action = _actions[tank.side][tank.id]
                if not tank.destroyed and Action.is_move(action):
                    self.remove_field(tank)
                    tank.x += _dx[action]
                    tank.y += _dy[action]
                    self.insert_field(tank)

        # 处理射击行为
        for tanks in self._tanks:
            for tank in tanks:
                action = _actions[tank.side][tank.id]
                if not tank.destroyed and Action.is_shoot(action):
                    x, y = tank.xy
                    action -= 4 # 使之与 dx, dy 的 idx 对应
                    while True:
                        x += _dx[action]
                        y += _dy[action]
                        if not self.in_map(x, y):
                            break
                        currentFields = self.get_fields(x, y)
                        if len(currentFields) == 0:
                            continue
                        elif len(currentFields) > 1: # 必定都是 tank
                            pass
                        else: # len(currentFields) == 1
                            field = currentFields[0]
                            if isinstance(field, (WaterField, EmptyField)):
                                continue # 跳过水路和空格
                            elif ( isinstance(field, TankField)
                                   and not self.has_multi_tanks(x, y)
                                   and not self.has_multi_tanks(*field.xy)
                                ): # 对射判断，此时两方所在格子均都只有一架坦克
                                oppTank = field
                                oppAction = _actions[oppTank.side][oppTank.id]
                                if ( Action.is_shoot(oppAction)
                                     and Action.is_opposite(action, oppAction)
                                    ):
                                    break # 对射抵消
                                else:
                                    pass # 坦克被摧毁
                            elif isinstance(field, SteelField):
                                break # 钢墙无法摧毁
                            elif isinstance(field, (BrickField, BaseField) ):
                                pass # 基地和土墙可以被摧毁
                            else:
                                raise Exception("unexpected field type")
                        _fieldsToBeDestroyed.update(currentFields)
                        break # 摧毁了第一个遇到的 fields

        for field in _fieldsToBeDestroyed:
            self.remove_field(field)

        #debug_print("End Turn: %s" % self._turn)
        #self.debug_print_out()


    def simulate_one_action(self, tank, action):
        """
        只执行其中一架 tank 的行为，其他 tank 均假设为不动
        """
        actions = [
            [Action.STAY for _ in range(TANKS_PER_SIDE) ] for __ in range(SIDE_COUNT)
        ]
        actions[tank.side][tank.id] = action
        self.perform(*actions)

    def revert(self):
        """
        回滚一回合的行为

        Return:
            - success   bool
        """
        if self._turn <= 0: # 可以为 1 ，此时回滚到 Turn 0 的结束点
            return False    # 这表示回到地图最初的状态

        currentTurn = self._turn
        records = self._destroyedRecords
        _actions = self._previousActions.pop()
        #simulator_print("revert turn:", self._turn, _actions)

        for side, tanks in enumerate(self._tanks): # 回滚历史动作
            for id_, tank in enumerate(tanks):
                tank.previousAction = _actions[side][id_]

        while len(records) > 0:
            if records[-1][0] == currentTurn:
                turn, (x, y), field = records.pop()
                if isinstance(field, TankField):
                    tank = field
                    if not tank.destroyed: # tank 发生移动
                        self.remove_field(tank, record=False)
                    tank.x = x
                    tank.y = y
                    self.insert_field(tank)
                else:
                    self.insert_field(field)
            else:
                break

        self._turn -= 1
        self.__clean_cache()

        #debug_print("Revert to Turn: %s" % self._turn) # 至 turn 的结束状态
        #self.debug_print_out()

        return True


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


    def debug_print_out(self, compact=COMPACT_MAP):
        """
        [DEBUG] 输出整个地图

        Input:
            - compact   bool   是否以紧凑的形式输出
        """
        if not DEBUG_MODE:
            return

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



#{ BEGIN 'strategy/signal.py' }#

class Signal(object):
    pass

#{ END 'strategy/signal.py' }#



#{ BEGIN 'strategy/utils.py' }#

''' # Migrate to BattleTank.get_destroyed_fields_if_shoot
def get_destroyed_fields(tank, action, map):
    """
    下一回合某坦克执行一个射击行为后，将会摧毁的 fields

    用于单向分析 action 所能造成的影响，不考虑对方下一回合的决策

    - 不判断自身是否与其他 tank 重叠
    - 如果对方是 tank 认为对方下回合不开炮

    Return:
        - fields   [Field]/[]   被摧毁的 fields
                                如果没有对象被摧毁，则返回空列表
    """
    map_ = map
    assert map_.is_valid_shoot_action(tank, action)

    action -= 4 # 使之与 dx, dy 的 idx 对应
    x, y = tank.xy
    dx, dy = Action.DIRECTION_OF_ACTION_XY[action]

    while True: # 查找该行/列上是否有可以被摧毁的对象
        x += dx
        y += dy
        if not map_.in_map(x, y):
            break
        currentFields = map_[x, y]
        if len(currentFields) == 0: # 没有对象
            continue
        elif len(currentFields) > 1: # 均为坦克
            return currentFields
        else: # len == 1
            field = currentFields[0]
            if isinstance(field, (WaterField, EmptyField) ): # 空对象或水路
                continue
            elif isinstance(field, SteelField): # 钢墙不可摧毁
                return []
            else:
                return currentFields

    return [] # 没有任何对象被摧毁
'''


def is_block_in_route(field, route):
    """
    判断一个 Brick/Base/Tank (具体由寻找路线时的函数决定) 是否为相应路线上，为一个
    block type 也就是必须要射击一次才能消灭掉的 field 对象。

    Input:
        - field    Field    地图上某个对象
        - route    [(x: int, y: int, weight: int, BFSAction: int)]   带权重值的路径
    """
    for x, y, weight, BFSAction in route:
        if (x, y) == field.xy:
            if weight >= 2 and BFSAction == MOVE_ACTION_ON_BFS: # 移动受阻的
                return True # 移动受阻，需要两个回合（及以上）
            elif weight >= 1 and BFSAction == SHOOT_ACTION_ON_BFS: # 射击受阻
                return True # 射击受阻，需要一个回合（及以上）（通常两回合，但是目标物可算作一回合）
    return False


def fake_map_matrix_T_without_enemy(map, mySide):
    """
    伪造一个没有敌方坦克的地图类型矩阵

    WARNING:
        首先检查是不是对方 tank ，因为可能遇到对方已经死亡或者两方坦克重合
        这种时候如果己方坦克恰好在这个位置，就会被删掉，assert 不通过
    """
    map_ = map
    oppSide = 1 - mySide
    cMatrixMap = map_.matrix_T.copy()
    for oppTank in map_.tanks[oppSide]:
        if cMatrixMap[oppTank.xy] == Field.TANK + 1 + oppSide:
            cMatrixMap[oppTank.xy] = Field.EMPTY
    return cMatrixMap

#{ END 'strategy/utils.py' }#



#{ BEGIN 'strategy/bfs.py' }#

DEFAULT_BLOCK_TYPES       = ( Field.STEEL, Field.WATER, )
DEFAULT_DESTROYABLE_TYPES = ( Field.BRICK, )
#------------------------
# 通常需要额外考虑的类型有
#
# 1. 两方基地
# 2. 己方坦克和对方坦克
#------------------------

INFINITY_WEIGHT       = -1 # 无穷大的权重，相当于不允许到达
INFINITY_ROUTE_LENGTH = -1 # 无穷大的路径长度，相当于无法找到

DUMMY_ACTION_ON_BFS = -2 # 空行为
NONE_ACTION_ON_BFS  = -1 #　上回合什么都不做，相当于停止，专门用于 start == end 的情况
MOVE_ACTION_ON_BFS  = 0  # 上一回合操作标记为搜索
SHOOT_ACTION_ON_BFS = 1  # 上一回合操作标记为射击


def _BFS_search_for_move(start, end, map_matrix_T, weight_matrix_T,
                         block_types=DEFAULT_BLOCK_TYPES):
    """
    BFS 搜索从 start -> end 的最短路径，带权重
    ----------------------------------------------------------------------------

    Input:

        - start         (int, int)      起始坐标 (x1, y2)

        - end           (int, int)      终点坐标 (x2, y2) ，其对应的 field 类型必须不在
                                        block_types 的定义里，否则查找到的路径为空

        - map_matrix_T      np.array( [[int]] )   field 类型值的矩阵的转置，坐标形式 (x, y)

        - weight_matrix_T   np.array( [[int]] )   每个格子对应节点的权重，形状与坐标形式同上

        - block_types       [int]       不能够移动到的 field 类型
                                        WARNING:
                                            需要自行指定不能够到达的基地、坦克的类型

    Return:

        - dummy_tail        Node        end 节点后的空节点：
                                        -------------------
                                        1. 如果本次搜索找到路径，则其 parent 属性指向 end 节点，
                                        可以连成一条 endNode -> startNode 的路径。
                                        2. 如果传入的 start == end 则 startNode == endNode
                                        这个节点的 parent 指向 startNode 。
                                        3. 如果没有搜索到可以到达的路线，则其 parent 值为 None

    ----------------------------------------------------------------------------

    def struct Node: // 定义节点模型
    [
        "xy":     (int, int)          目标节点
        "parent": Node/None           父节点
        "step":   int ( >= 0 )        还差几步到达，为 0 表示到达，初始值为 weight - 1
        "weight": const int ( >= 1 )  权重，即搜索时需要在其上耗费的步数
        "last_action": const int      通过什么操作到达这个节点，该情况为移动
    ]

    """
    x1, y1 = start
    x2, y2 = end

    width, height = map_matrix_T.shape # width, height 对应着转置前的 宽高

    matrixMap = map_matrix_T
    matrixWeight = weight_matrix_T

    matrixCanMoveTo = np.ones_like(matrixMap, dtype=np.bool8)
    for _type in block_types:
        matrixCanMoveTo &= (matrixMap != _type)

    '''
    debug_print("map:\n", matrixMap.T)
    debug_print("weight:\n", matrixWeight.T)
    debug_print("can move on:\n", matrixCanMoveTo.astype(np.int8).T)
    '''

    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION_ON_BFS,
        ]

    dummyTail = [ # end 节点后的空节点
        (-1, -1),
        None, #　当找到 end 的时候，这个值指向 end，否则保持为 None
        -1,
        -1,
        DUMMY_ACTION_ON_BFS,
        ]

    queue  = deque() # queue( [Node] )
    matrixMarked = np.zeros_like(matrixMap, dtype=np.bool8)

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init

    while len(queue) > 0:

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if matrixMarked[x, y]:
            continue
        matrixMarked[x, y] = True

        if DEBUG_MODE:
            matrixDistance[x, y] = _get_route_length_by_node_chain(node)

        if (x, y) == end: # 到达终点
            dummyTail[1] = node
            break

        for dx, dy in DIRECTIONS_URDL:
            x, y = node[0]
            x3 = x + dx
            y3 = y + dy
            if (not (0 <= x3 < width and 0 <= y3 < height) # not in map
                or not matrixCanMoveTo[x3, y3]
                ):
                continue
            weight = matrixWeight[x3, y3]
            queue.append([
                (x3, y3),
                node,
                weight-1,
                weight,
                MOVE_ACTION_ON_BFS,
                ])
    '''
    if DEBUG_MODE:
        debug_print("distance matrix:\n", matrixDistance.T)
    '''

    return dummyTail


def _BFS_search_for_shoot(start, end, map_matrix_T, move_weight_matrix_T,
                          shoot_weight_matrix_T, block_types=DEFAULT_BLOCK_TYPES,
                          destroyable_types=DEFAULT_DESTROYABLE_TYPES):
    """
    BFS 搜索从 start 开始到击中 end 的最短路线，带权重
    ----------------------------------------------------------------------------

    实现思路：

    首先，我们可以认为，射击的方式能够比移动的方式更快地接近目标，毕竟炮弹是飞行的。
    而能够直接向目标发动射击的位置，仅仅位于与它同一行或同一列的位置上，因此，搜索的思路是，
    对于所有可以向目标发起进攻的坐标，分别找到从起点移动到这些坐标的最短路径，然后接着以射击
    的方式，找到从这些射击点到达目标点的路径（这种路径可以抽象地认为是炮弹飞行的路径），
    然后从中找到最短的一条路径（对于射击来讲，距离可以理解为就是开炮和冷却的回合），
    该路径即为所求的。

    ---------------------------------------------------------------------------

    Input:

        - start         (int, int)      起始坐标 (x1, y2)

        - end           (int, int)      终点坐标 (x2, y2) ，其对应的 field 类型必须不在
                                        destroyable_types 的定义里，否则查找到的路径为空

        - map_matrix_T            np.array( [[int]] )   field 类型值的矩阵的转置，坐标形式 (x, y)

        - move_weight_matrix_T    np.array( [[int]] )   移动到这个格子所需的步数

        - shoot_weight_matrix_T   np.array( [[int]] )   炮弹到达这个格子所需的步数

        - block_types           [int]   不能够移动到的 field 类型
                                        WARNING:
                                            需要自行指定不能被攻击的基地、坦克的类型

        - destroyable_types     [int]   能够通过射击行为摧毁的 field 类型，未指定在这个变量里的
                                        所有其他 field 类型均默认视为不可摧毁，在以射击的方式进行
                                        搜索时，遇到这样的 field 会跳过
                                        WARNING:
                                            需要自行制定可以被摧毁的基地、坦克的类型

    Return:

        - dummy_tail        Node        end 节点后的空节点：
                                        -------------------
                                        1. 如果本次搜索找到路径，则其 parent 属性指向 end 节点，
                                        可以连成一条 endNode -> startNode 的路径。
                                        2. 如果传入的 start == end 则 startNode == endNode
                                        这个节点的 parent 指向 startNode 。
                                        3. 如果没有搜索到可以到达的路线，则其 parent 值为 None

    --------------------------------------------------------------------------

    def struct Node: // 定义节点模型
    [
        "xy":     (int, int)          目标节点
        "parent": Node/None           父节点
        "step":   int ( >= 0 )        还差几步到达，为 0 表示到达，初始值为 weight - 1
        "weight": const int ( >= 1 )  权重，即搜索时需要在其上耗费的步数
        "last_action": const int      通过什么操作到达这个节点，射击或移动
    ]

    """
    x1, y1 = start
    x2, y2 = end

    width, height = map_matrix_T.shape
    matrixMap = map_matrix_T
    matrixMoveWeight = move_weight_matrix_T
    matrixShootWeight = shoot_weight_matrix_T

    # 哪些位置可以移动到
    matrixCanMoveTo = np.ones_like(matrixMap, dtype=np.bool8)
    for _type in block_types:
        matrixCanMoveTo &= (matrixMap != _type)

    # 那些位置上的 field 可以被摧毁
    matrixCanBeDestroyed = np.zeros_like(matrixMap, dtype=np.bool8)
    for _type in destroyable_types:
        matrixCanBeDestroyed |= (matrixMap == _type)

    # 哪些位置可以对目标发动射击，即 end 向四个方向伸展开的区域
    matrixCanShoot = np.zeros_like(matrixMap, dtype=np.bool8)
    matrixCanShoot[x2, y2] = True
    for dx, dy in DIRECTIONS_URDL:
        x, y = end
        while True:
            x += dx
            y += dy
            if not (0 <= x < width and 0 <= y < height):
                break
            elif matrixMap[x, y] == Field.EMPTY: # 空对象
                pass
            elif not matrixCanBeDestroyed[x, y]:
                break
            matrixCanShoot[x, y] = True

    '''
    debug_print("map:\n", matrixMap.T)
    debug_print("weight of move:\n", matrixMoveWeight.T)
    debug_print("weight of shoot:\n", matrixShootWeight.T)
    debug_print("can move to:\n", matrixCanMoveTo.astype(np.int8).T)
    debug_print("can shoot:\n", matrixCanShoot.astype(np.int8).T)
    debug_print("can be destroyed:\n", matrixCanBeDestroyed.astype(np.int8).T)
    '''

    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION_ON_BFS, # 对于 start == end 的情况，将返回 startNode，相当于原地等待
        ]

    dummyTail = [
        (-1, -1),
        None,
        -1,
        -1,
        DUMMY_ACTION_ON_BFS,
        ]

    queue  = deque() # queue( [Node] )
    matrixMarked = np.zeros_like(matrixMap, dtype=np.bool8)
    canShootNodeChains = {} # { (x, y): Node } 从 start 到每一个可射击点的最短路线

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init


    ## 首先通过常规的 BFS 搜索，确定到达每一个射击点的最短路径

    while len(queue) > 0:

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if matrixMarked[x, y]:
            continue
        matrixMarked[x, y] = True

        if matrixCanShoot[x, y]:
            canShootNodeChains[(x, y)] = node  # 记录最短节点

        if DEBUG_MODE:
            matrixDistance[x, y] = _get_route_length_by_node_chain(node)

        for dx, dy in DIRECTIONS_URDL:
            x, y = node[0]
            x3 = x + dx
            y3 = y + dy
            if (not (0 <= x3 < width and 0 <= y3 < height) # not in map
                or not matrixCanMoveTo[x3, y3]
                ):
                continue

            weight = matrixMoveWeight[x3, y3]
            if weight == INFINITY_WEIGHT:
                continue

            queue.append([
                (x3, y3),
                node,
                weight-1,
                weight,
                MOVE_ACTION_ON_BFS,
                ])

    ## 接下来对于每个节点，尝试通过射击的方式走完剩下的路程

    reachTargetNodeChains = [] # 收集所有可以成功射击到基地的路线

    for xy, node in canShootNodeChains.items():

        if xy == end:
            reachTargetNodeChains.append(node)
            continue

        # 确定攻击方向
        x3, y3 = xy
        dx = np.sign(x2 - x3)
        dy = np.sign(y2 - y3)

        while True:
            x3 += dx
            y3 += dy
            weight = matrixShootWeight[x3, y3]

            node = [ # 走到下一个节点
                (x3, y3),
                node,
                weight-1, # 补偿
                weight,
                SHOOT_ACTION_ON_BFS,
                ]

            if (x3, y3) == end: # 到达目标
                reachTargetNodeChains.append(node)
                break

    ## 找到最短的路径

    '''
    if DEBUG_MODE:
        debug_print("distance matrix:\n", matrixDistance.T)
    '''

    dummyTail[1] = min(reachTargetNodeChains, # 最短路径
                        key=lambda node: _get_route_length_by_node_chain(node))

    return dummyTail


def find_shortest_route_for_move(start, end, matrix_T,
                                 block_types=DEFAULT_BLOCK_TYPES):
    """
    搜索移动到目标的最短路线

    Input:
        - matrix_T   np.array( [[int]] )   游戏地图的类型矩阵的转置

    Return:
        - route   [(x: int, y: int, weight: int, BFSAction: int)]   带权重值的路径
    """
    matrixMap = matrix_T

    matrixWeight = np.ones_like(matrixMap)
    matrixWeight[matrixMap == Field.BRICK] = 1 + 1 # 射击一回合，移动一回合
    matrixWeight[matrixMap == Field.STEEL] = INFINITY_WEIGHT
    matrixWeight[matrixMap == Field.WATER] = INFINITY_WEIGHT

    dummyTail = _BFS_search_for_move(start, end, matrixMap, matrixWeight,
                                    block_types=block_types)

    route = []
    node = dummyTail
    while True:
        node = node[1]
        if node is not None:
            x, y      = node[0]
            weight    = node[3]
            BFSAction = node[4]
            route.append( (x, y, weight, BFSAction) )
        else:
            break
    route.reverse()
    return route


def find_shortest_route_for_shoot(start, end, matrix_T,
                                  block_types=DEFAULT_BLOCK_TYPES,
                                  destroyable_types=DEFAULT_DESTROYABLE_TYPES):
    """
    搜索移动并射击掉目标的最短路线

    """
    matrixMap = matrix_T

    matrixMoveWeight = np.ones_like(matrixMap)   # weight 默认为 1，即移动一回合
    matrixMoveWeight[matrixMap == Field.BRICK]   = 1 + 1  # 射击一回合，移动一回合
    matrixMoveWeight[matrixMap == Field.STEEL]   = INFINITY_WEIGHT
    matrixMoveWeight[matrixMap == Field.WATER]   = INFINITY_WEIGHT

    matrixShootWeight = np.zeros_like(matrixMap) # weight 默认为 0 ，即炮弹可以飞过
    matrixShootWeight[matrixMap == Field.BRICK]  = 1 + 1  # 射击一回合，冷却一回合
    matrixShootWeight[matrixMap == Field.STEEL]  = INFINITY_WEIGHT
    for _type in BASE_FIELD_TYPES:
        matrixShootWeight[matrixMap == _type]    = 1      # 射击一回合，之后就赢了
    for _type in TANK_FIELD_TYPES:
        matrixShootWeight[matrixMap == _type]    = 1 + 1  # 射击一回合，冷却一回合
    # WARNING:
    #   这里只是从理论上分析 TANK, BASE 被打掉对应的权重，实际上我们不希望基地和队友
    #   被打掉，因此在实际使用时，仅仅在 destroyable_types 中添加敌方的坦克即可


    dummyTail = _BFS_search_for_shoot(start, end, matrixMap, matrixMoveWeight,
                                    matrixShootWeight, block_types=block_types,
                                    destroyable_types=destroyable_types)
    route = []
    node = dummyTail
    while True:
        node = node[1]
        if node is not None:
            x, y      = node[0]
            weight    = node[3]
            BFSAction = node[4]
            route.append( (x, y, weight, BFSAction) )
        else:
            break
    route.reverse()
    return route


def get_route_length(route):
    """
    计算路线长度

    Input:
        - route    [(x: int, y: int, weight: int, BFSAction: int)]   带权重值的路径，从 start -> end

    Return:
        - length   int   路线长度，如果是空路线，返回 无穷大长度
    """
    if len(route) == 0:
        return INFINITY_ROUTE_LENGTH
    return np.sum( r[2] for r in route )


def _get_route_length_by_node_chain(node):
    """
    [DEBUG] 传入 node head ，计算其所代表的节点链对应的距离
    """
    assert isinstance(node, list) and len(node) == 5
    dummyTail = [
        (-1, -1),
        node,
        -1,
        -1,
        DUMMY_ACTION_ON_BFS,
        ]
    route = []
    node = dummyTail
    while True:
        node = node[1]
        if node is not None:
            x, y   = node[0]
            weight = node[3]
            route.append( (x, y, weight) )
        else:
            break
    return get_route_length(route)

#{ END 'strategy/bfs.py' }#



#{ BEGIN 'strategy/estimate.py' }#

AGGRESSIVE_STATUS = 1
STALEMATE_STATUS  = 0
DEFENSIVE_STATUS  = -1


def assess_aggressive(battler, oppBattler):
    """
    根据敌我两架坦克的攻击线路长短，衡量当前侵略性

    Input:
        - battler      BattleTank
        - oppBattler   BattleTank

    Return:
        - AGGRESSIVE_STATUS   我方处于攻击状态
        - STALEMATE_STATUS    双方处于僵持状态
        - DEFENSIVE_STATUS    我方处于防御状态
    """
    myRoute = battler.get_shortest_attacking_route()
    oppRoute = oppBattler.get_shortest_attacking_route()
    myRouteLen = get_route_length(myRoute)
    oppRouteLen = get_route_length(oppRoute)
    simulator_print(battler, "delta routeLen:", oppRouteLen - myRouteLen)
    # TODO:
    #   阈值不可定的太小，否则可能是错误估计，因为对方如果有防守，
    #   就有可能拖延步数。很有可能需要再动态决策一下，尝试往前预测几步，看看
    #   会不会受到阻碍，然后再下一个定论
    if oppRouteLen - myRouteLen >= 1: # TODO: 阈值多少合理？
        return AGGRESSIVE_STATUS
    elif myRouteLen - oppRouteLen > 1: # TODO: 阈值？
        return DEFENSIVE_STATUS
    else:
        return STALEMATE_STATUS

#{ END 'strategy/estimate.py' }#



#{ BEGIN 'strategy/abstract.py' }#

class Strategy(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
        raise NotImplementedError


class SingleTankStrategy(Strategy):
    """
    不考虑其他 tank 的情况，某一 tank 单独决策

    """
    def __init__(self, tank, map, **kwargs):
        """
        Input:
            - tank   TankField   需要做出决策的 tank
            - map    Tank2Map    当前地图
        """
        self._tank = tank
        self._map = map

    def make_decision(self, *args, **kwargs):
        """
        该 tank 单独做出决策

        Return:
            - action   int   Action 类中定义的动作编号
                             如果判断到在这种情况下不适合使用该策略，则返回 Action.INVALID
        """
        raise NotImplementedError

#{ END 'strategy/abstract.py' }#



#{ BEGIN 'tank.py' }#

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

#{ END 'tank.py' }#



#{ BEGIN 'player.py' }#

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

#{ END 'player.py' }#



#{ BEGIN 'team.py' }#

class Team(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
        raise NotImplementedError


class Tank2Team(Team):


    def __init__(self, side, player1, player2):
        self._side = side
        self._player1 = player1
        self._player2 = player2
        self._opponentTeam = None

    @property
    def side(self):
        return self._side

    def set_opponent_team(self, team):
        """
        设置对手团队

        Input:
            - team    Tank2Team
        """
        assert isinstance(team, self.__class__)
        self._opponentTeam = team

    def make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """

        action1 = self._player1.make_decision()
        action2 = self._player2.make_decision()

        # TODO:
        # ------------
        #   团队策略 !!!

        if action1 == Action.INVALID:
            action1 = Action.STAY
        if action2 == Action.INVALID:
            action2 = Action.STAY
        return [ action1, action2 ]

#{ END 'team.py' }#



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
        self._pastActions = {
            (side, id_): [] for side in range(SIDE_COUNT)
                            for id_ in range(TANKS_PER_SIDE)
        }

    @property
    def turn(self):
        return self._map.turn

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

        assert len(self._requests) - len(self._responses) == 1 # 带 header

        header = self._requests.pop(0) # 此时 header 被去掉

        self._mySide = header["mySide"]
        assert self._mySide in (0, 1), "unexpected mySide %s" % self._mySide

        for key, _Field in [("brickfield", BrickField),
                            ("steelfield", SteelField),
                            ("waterfield", WaterField),]:
            for x, y in self._parse_field_points(header[key]):
                self._map.insert_field(_Field(x, y))

        if self._mySide == 0:
            allBlueActions = self._responses
            allRedActions  = self._requests
        elif self._mySide == 1:
            allBlueActions = self._requests
            allRedActions  = self._responses

        for blueActions, redActions in zip(allBlueActions, allRedActions):
            self._map.perform(blueActions, redActions)

        if not len(allBlueActions) == len(allRedActions) == 0:
            b0, b1 = zip(*allBlueActions)
            r0, r1 = zip(*allRedActions)
            self._pastActions = { # { (side, id): [Action] }
                (0, 0): b0, (0, 1): b1,
                (1, 0): r0, (1, 1): r1,
            }

    def make_output(self, actions, stream=sys.stdout,
                    debug=None, data=None, globaldata=None):
        super().make_output(stream, actions, debug, data, globaldata)

    def get_past_actions(self, side, id):
        """
        获得某一坦克的历史决策
        """
        return self._pastActions.get( (side, id), [] ) # 没有记录则抛出 []

#{ END 'botzone.py' }#



#{ BEGIN 'main.py' }#

def main(istream=None, ostream=None):

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_, long_running=LONG_RUNNING_MODE)

    istream = istream or BotzoneIstream()
    ostream = ostream or BotzoneOstream()

    while True:

        t1 = time.time()

        if LONG_RUNNING_MODE: # 这个模式下 map 对象会复用，首先需要重置
            map_.reset()

        terminal.handle_input(stream=istream)

        if SIMULATOR_ENV:
            map_.debug_print_out()

        side = terminal.mySide
        tanks = map_.tanks

        bluePlayer0 = Tank2Player(tanks[BLUE_SIDE][0], map_, terminal.get_past_actions(BLUE_SIDE, 0))
        bluePlayer1 = Tank2Player(tanks[BLUE_SIDE][1], map_, terminal.get_past_actions(BLUE_SIDE, 1))
        redPlayer0  = Tank2Player(tanks[RED_SIDE][0], map_, terminal.get_past_actions(RED_SIDE, 0))
        redPlayer1  = Tank2Player(tanks[RED_SIDE][1], map_, terminal.get_past_actions(RED_SIDE, 1))

        bluePlayer0.set_teammate(bluePlayer1)
        bluePlayer1.set_teammate(bluePlayer0)
        redPlayer0.set_teammate(redPlayer1)
        redPlayer1.set_teammate(redPlayer0)
        bluePlayer0.set_opponents([redPlayer0, redPlayer1])
        bluePlayer1.set_opponents([redPlayer0, redPlayer1])
        redPlayer0.set_opponents([bluePlayer0, bluePlayer1])
        redPlayer1.set_opponents([bluePlayer0, bluePlayer1])

        blueTeam = Tank2Team(BLUE_SIDE, bluePlayer0, bluePlayer1)
        redTeam  = Tank2Team(RED_SIDE, redPlayer0, redPlayer1)
        blueTeam.set_opponent_team(redTeam)
        redTeam.set_opponent_team(blueTeam)

        if side == BLUE_SIDE:
            myPlayer0 = bluePlayer0
            myPlayer1 = bluePlayer1
            myTeam    = blueTeam
            oppTeam   = redTeam
        elif side == RED_SIDE:
            myPlayer0 = redPlayer0
            myPlayer1 = redPlayer1
            myTeam    = redTeam
            oppTeam   = blueTeam
        else:
            raise Exception("unexpected side %s" % side)

        actions = myTeam.make_decision()

        if SIMULATOR_ENV:
            oppActions = oppActions = oppTeam.make_decision()

        if SIMULATOR_ENV:
            _CUT_OFF_RULE = "-" * 20
            simulator_print("Decisions for next turn:")
            simulator_print(_CUT_OFF_RULE)
            _SIDE_NAMES = ["Blue", "Red"]
            for id_, action in enumerate(actions):
                simulator_print("%s %02d: %s" % (_SIDE_NAMES[side], id_+1,
                                    Action.get_name(action)) )
            for id_, action in enumerate(oppActions):
                simulator_print("%s %02d: %s" % (_SIDE_NAMES[1-side], id_+1,
                                    Action.get_name(action)))
            simulator_print(_CUT_OFF_RULE)
            simulator_print("Actually actions on this turn:")
            simulator_print(_CUT_OFF_RULE)
            for side, tanks in enumerate(map_.tanks):
                for id_, tank in enumerate(tanks):
                    simulator_print("%s %02d: %s" % (_SIDE_NAMES[side], id_+1,
                                        Action.get_name(tank.previousAction)))
            simulator_print(_CUT_OFF_RULE)


        t2 = time.time()

        debugInfo = {
            "cost": round(t2-t1, 4),
            }

        terminal.make_output(actions, stream=ostream, debug=debugInfo)


if __name__ == '__main__':
    main()

#{ END 'main.py' }#



