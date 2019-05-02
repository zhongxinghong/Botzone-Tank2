# -*- coding: utf-8 -*-
# @Author:   Rabbit
# @Filename: botzone_tank2.py
# @Date:     2019-05-03 05:44:29
# @Description: Auto-built single-file Python script for Botzone/Tank2
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

#{ END 'const.py' }#



#{ BEGIN 'global_.py' }#

import time
import sys
import json
import random
import pickle
import base64
import gzip
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


class SingletonMeta(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(SingletonMeta, cls).__call__(*args)
        return cls._instance[cls]


class UniqueIntEnumMeta(type):
    """
    使得枚举类内所有的 int 值都增加一个 __offset__ 偏移量
    使得不同的枚举类可以用同样的 int 值申明 case，但是不同枚举类间，实际的属性值不同不同

    需要在类属性中通过 __offset__ 值申明偏移量

    """
    def __new__(cls, name, bases, attrs):
        offset = attrs.get("__offset__", 0) # 默认为 0
        for k, v in attrs.items():
            if isinstance(v, int):
                attrs[k] += offset
        return super(UniqueIntEnumMeta, cls).__new__(cls, name, bases, attrs)


class DataSerializer(object):

    @staticmethod
    def _unpad(s):
        return s.rstrip("=")

    @staticmethod
    def _pad(s):
        return s + "=" * ( 4 - len(s) % 4 )

    @staticmethod
    def serialize(obj):
        return __class__._unpad(
                    base64.b64encode(
                        gzip.compress(
                            pickle.dumps(obj))).decode("utf-8"))

    @staticmethod
    def deserialize(s):
        return pickle.loads(
                    gzip.decompress(
                        base64.b64decode(
                            __class__._pad(s).encode("utf-8"))))

#{ END 'utils.py' }#



#{ BEGIN 'action.py' }#

class Action(object):

    # 推迟决策
    POSTPONE    = -4 # 用于告知 Team 让队友优先决策

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

    # 方便用于迭代
    MOVE_ACTIONS  = ( MOVE_UP,  MOVE_RIGHT,  MOVE_DOWN,  MOVE_LEFT  )
    SHOOT_ACTIONS = ( SHOOT_UP, SHOOT_RIGHT, SHOOT_DOWN, SHOOT_LEFT )
    VALID_ACTIONS = ( STAY, ) + MOVE_ACTIONS + SHOOT_ACTIONS


    _ACTION_NAMES = [

        "Invalid",  "Stay",
        "Up Move",  "Right Move",  "Down Move",  "Left Move",
        "Up Shoot", "Right Shoot", "Down Shoot", "Left Shoot",

        ]

    @staticmethod
    def is_valid(action): # 是否为有效行为
        return -1 <= action <= 7

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
            raise Exception("can't move from (%s, %s) to (%s, %s) in one turn"
                             % (x1, y1, x2, y2) )

    @staticmethod
    def get_move_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的射击行为
        这个就是对 get_action 的命名，这出于历史遗留问题 ...
        """
        return __class__.get_action(x1, y1, x2, y2)

    @staticmethod
    def get_shoot_action(x1, y1, x2, y2):
        """
        获得 (x1, y1) -> (x2, y2) 的射击行为
        """
        return __class__.get_action(x1, y1, x2, y2) + 4

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


class Tank2Map(Map, metaclass=SingletonMeta):

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
                    matrix[y, x] = Field.MULTI_TANK # 重合视为一个坦克
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

        Input:
            - tank     TankField/BattleTank   能表明坐标的 tank 对象
            - action   int                    下回合的行动
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

class Signal(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 200

    NONE        = 0   # 空信号
    UNHANDLED   = 1   # 未处理团队信号，通常是因为有更紧急的状况而没有运行到相应的处理信号的位置
    CANHANDLED  = 2   # 未能处理团队信号，通常是因为尝试处理但是发现不合适


    PREPARE_FOR_BREAK_BRICK = 11 # 准备破墙，也就是准备给自己寻找后路
    READY_TO_PREPARE_FOR_BREAK_BRICK = 12 # 准备好为破墙而凿开两边墙壁
    READY_TO_BREAK_BRICK = 13  # 准备要破墙


    PREPARE_FOR_BREAK_OVERLAP = 14  # 团队向队员发信号，希望能马上打破重叠
    READY_TO_BREAK_OVERLAP    = 15  # 准备要主动打破重叠


    BREAK_SIGNALS = ( UNHANDLED, CANHANDLED )

    @staticmethod
    def is_break(signal):
        """
        该信号是否意味着沟通停止
        也就是是否为未处理或无法处理
        """
        return signal in __class__.BREAK_SIGNALS

#{ END 'strategy/signal.py' }#



#{ BEGIN 'strategy/status.py' }#

class Status(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 100

    NONE       = 0  # 空状态

    AGGRESSIVE = 1  # 侵略性的
    DEFENSIVE  = 2  # 防御性的
    STALEMENT  = 3  # 僵持的
    DYING      = 4  # 准备要挂了
    DIED       = 5  # 已经挂了

    REALODING  = 9  # 正在装弹，下回合无法射击

    ENCOUNT_ENEMY      = 11
    ENCOUNT_ONE_ENEMY  = 12
    ENCOUNT_TWO_ENEMY  = 13
    OVERLAP_WITH_ENEMY = 14

    KEEP_ON_MARCHING       = 21  # 继续行军
    READY_TO_ATTACK_BASE   = 22  # 准备拆基地
    READY_TO_FIGHT_BACK    = 23  # 准备反击
    READY_TO_DODGE         = 24  # 准备闪避敌人
    READY_TO_KILL_ENEMY    = 25  # 准备击杀敌人
    READY_TO_BLOCK_ROAD    = 26  # 准备堵路
    KEEP_ON_OVERLAPPING    = 27  # 等待与自己重叠的敌人的决策
    WAIT_FOR_MARCHING      = 28  # 存在风险，等待进攻
    HAS_ENEMY_BEHIND_BRICK = 29  # 隔墙有人
    PREVENT_BEING_KILLED   = 30  # 为了防止被射击而停下
    HUNTING_ENEMY          = 31  # 主动追杀敌军

    READY_TO_PREPARE_FOR_BREAK_BRICK = 41 # 准备为破墙而准备闪避路线
    READY_TO_BREAK_BRICK   = 42 # 准备破墙
    READY_TO_BREAK_OVERLAP = 43 # 准备主动打破重叠

    ANTICIPATE_TO_KILL_ENEMY = 50 # 主动防御时，尝试击杀敌军，这个状态可以用来记忆行为
    BLOCK_ROAD_FOR_OUR_BASE  = 51 # 主动防御时，遇到敌方面向基地，但没有炮弹，自己又恰好能阻挡在中间
    SACRIFICE_FOR_OUR_BASE   = 52 # 主动防御时，遇到敌方下一炮打掉基地，自己又恰好能阻挡


    __Status_Name_Cache = None

    @staticmethod
    def get_name(status):
        """
        通过状态值自动判定方法
        """
        if __class__.__Status_Name_Cache is None:
            cache = __class__.__Status_Name_Cache = {}
            for k, v in __class__.__dict__.items():
                if not k.startswith("__"):
                    if isinstance(v, int):
                        key = k.title()
                        cache[v] = key
        cache = __class__.__Status_Name_Cache
        return cache.get(status, None) # 应该保证一定有方法？

#{ END 'strategy/status.py' }#



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



#{ BEGIN 'strategy/search.py' }#

# y-axis first / vertical first / aggressive
DIRECTIONS_URDL = ( (0, -1), ( 1, 0), (0,  1), (-1, 0) ) # 上右下左
DIRECTIONS_ULDR = ( (0, -1), (-1, 0), (0,  1), ( 1, 0) ) # 上左下右
DIRECTIONS_DRUL = ( (0,  1), ( 1, 0), (0, -1), (-1, 0) ) # 下右上左
DIRECTIONS_DLUR = ( (0,  1), (-1, 0), (0, -1), ( 1, 0) ) # 下左上右

# x-axis first / horizontal first / defensive
DIRECTIONS_RULD = ( ( 1, 0), (0, -1), (-1, 0), (0,  1) ) # 右上左下
DIRECTIONS_LURD = ( (-1, 0), (0, -1), ( 1, 0), (0,  1) ) # 左上右下
DIRECTIONS_RDLU = ( ( 1, 0), (0,  1), (-1, 0), (0, -1) ) # 右下左上
DIRECTIONS_LDRU = ( (-1, 0), (0,  1), ( 1, 0), (0, -1) ) #　左下右上

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


def get_searching_directions(x1, y1, x2=None, y2=None, x_axis_first=False):
    """
    获得从 (x1, y1) -> (x2, y2) 最优的搜索方向顺序

    Input:
        - (x1, y1)   起点坐标
        - (x2, y2)   终点坐标，可以没有，那么将通过 (x1, y1) 在地图中的相对位置，
                     对应着左上、左下、右上、右下四个区域，确定最佳的搜索顺序

        - x_axis_first   bool   是否采用 x 轴方向优先的搜索方式？默认以垂直方向优先，
                                也就是如果存在到达目标坐标的两条长度相同的路径，
                                会优先从 y 轴方向移动过去，即先上下移动，后左右移动。
                                若选择以水平方向优先，则先左右移动，后上下移动。

                                优先上下移动通常用于侵略，优先左右移动通常用于防御

    """
    if x2 is None or y2 is None:
        x3 = MAP_WIDTH  // 2 # 中点 x
        y3 = MAP_HEIGHT // 2 # 中点 y
        if   ( x3 - x1 >= 0 ) and ( y3 - y1 >= 0 ):
            return DIRECTIONS_DRUL if not x_axis_first else DIRECTIONS_RDLU
        elif ( x3 - x1 >= 0 ) and ( y3 - y1 <= 0 ):
            return DIRECTIONS_URDL if not x_axis_first else DIRECTIONS_RULD
        elif ( x3 - x1 <= 0 ) and ( y3 - y1 >= 0 ):
            return DIRECTIONS_DLUR if not x_axis_first else DIRECTIONS_LDRU
        elif ( x3 - x1 <= 0 ) and ( y3 - y1 <= 0 ):
            return DIRECTIONS_ULDR if not x_axis_first else DIRECTIONS_LURD
    else:
        if   ( x2 - x1 >= 0 ) and ( y2 - y1 >= 0 ):
            return DIRECTIONS_DRUL if not x_axis_first else DIRECTIONS_RDLU
        elif ( x2 - x1 >= 0 ) and ( y2 - y1 <= 0 ):
            return DIRECTIONS_URDL if not x_axis_first else DIRECTIONS_RULD
        elif ( x2 - x1 <= 0 ) and ( y2 - y1 >= 0 ):
            return DIRECTIONS_DLUR if not x_axis_first else DIRECTIONS_LDRU
        elif ( x2 - x1 <= 0 ) and ( y2 - y1 <= 0 ):
            return DIRECTIONS_ULDR if not x_axis_first else DIRECTIONS_LURD
    raise Exception


def _BFS_search_for_move(start, end, map_matrix_T, weight_matrix_T,
                         block_types=DEFAULT_BLOCK_TYPES, x_axis_first=False):
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

        - x_axis_first      bool        是否优先搜索 x 轴方向

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

        for dx, dy in get_searching_directions(x1, x2, y1, y2, x_axis_first=x_axis_first):
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
                          destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                          x_axis_first=False):
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

        - x_axis_first          bool    是否优先搜索 x 轴方向

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
    for dx, dy in get_searching_directions(x1, y1, x2, y2, x_axis_first=x_axis_first):
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

        for dx, dy in get_searching_directions(x1, y1, x2, y2, x_axis_first=x_axis_first):
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


def find_shortest_route_for_move(start, end, matrix_T, block_types=DEFAULT_BLOCK_TYPES,
                                 x_axis_first=False):
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
                                    block_types=block_types, x_axis_first=x_axis_first)

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
                                  destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                                  x_axis_first=False):
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
                                    destroyable_types=destroyable_types,
                                    x_axis_first=x_axis_first)
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

#{ END 'strategy/search.py' }#



#{ BEGIN 'strategy/estimate.py' }#

MINIMAL_TURNS_FOR_ACTIVE_DEFENSIVE_DECISION = 2


def assess_aggressive(battler, oppBattler):
    """
    根据敌我两架坦克的攻击线路长短，衡量当前侵略性

    Input:
        - battler      BattleTank
        - oppBattler   BattleTank

    Return:
        [status]
        - Status.AGGRESSIVE   我方处于攻击状态
        - Status.DEFENSIVE    我方处于防御状态
        - Status.STALEMENT    双方处于僵持状态
    """
    myRoute = battler.get_shortest_attacking_route()
    oppRoute = oppBattler.get_shortest_attacking_route()
    myRouteLen = get_route_length(myRoute)
    oppRouteLen = get_route_length(oppRoute)
    # debug_print(battler, "delta:", oppRouteLen - myRouteLen)
    # TODO:
    #   阈值不可定的太小，否则可能是错误估计，因为对方如果有防守，
    #   就有可能拖延步数。很有可能需要再动态决策一下，尝试往前预测几步，看看
    #   会不会受到阻碍，然后再下一个定论
    if oppRouteLen - myRouteLen >= 1: # TODO: 阈值多少合理？
        return Status.AGGRESSIVE
    elif myRouteLen - oppRouteLen > 1: # TODO: 阈值？
        return Status.DEFENSIVE
    else:
        return Status.STALEMENT

#{ END 'strategy/estimate.py' }#



#{ BEGIN 'tank.py' }#

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


    def break_brick_for_dodge(self, oppTank):
        """
        尝试凿开两边墙壁，以闪避敌人进攻

        适用条件：
            自己处在 WAIT_FOR_MARCHING 状态，身边没有遇敌的时候
        """
        tank = self._tank
        map_ = self._map
        oppBase = map_.bases[1 - tank.side]
        x1, y1 = tank.xy
        x2, y2 = oppTank.xy
        actions = []
        for dx, dy in get_searching_directions(x1, y1, oppBase.x, oppBase.y):
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

        x1, y1 = tank.xy
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action % 4]

        # 墙的位置
        x2 = x1 + dx
        y2 = y1 + dy

        # 墙后的位置
        x3 = x2 + dx
        y3 = y2 + dy

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
            if isinstance(field, TankField) and field.side != tank.side:
                return field
            else:
                return None

        return None


    def has_enemy_behind_brick(self, action):
        return self.get_enemy_behind_brick(action) is not None


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

#{ END 'player.py' }#



#{ BEGIN 'team.py' }#

class Team(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
        raise NotImplementedError


class Tank2Team(Team):

    def __init__(self, side, player1, player2, map):
        player1.set_team(self)
        player2.set_team(self)
        self._side = side
        self._map = map
        self._player1 = player1
        self._player2 = player2
        self._opponentTeam = None
        self._memory = {} # 团队记忆

    @property
    def side(self):
        return self._side

    @property
    def players(self):
        return [ self._player1, self._player2 ]

    def load_memory(self, memory):
        """
        botzone 将 data 传入给 team 恢复记忆
        """
        if memory is None:
            memory = {
                "status":  [] # [ set(), set() ] 每轮的状态
                }
        self._memory = memory


    def dump_memory(self):
        memory = self._memory
        memory["status"].append([
                self._player1.get_status(),
                self._player2.get_status(),
                ])
        return memory

    def get_memory(self):
        return self._memory

    def set_opponent_team(self, team):
        """
        设置对手团队

        Input:
            - team    Tank2Team
        """
        assert isinstance(team, self.__class__)
        self._opponentTeam = team


    def has_status_in_previous_turns(self, player, status, turns=1):
        """
        在曾经的一定回合里，某玩家是否拥有某个状态

        Input:
            - player   Player   玩家实例，不一定是本队的
            - status   int      状态编号
            - turns    int      向前检查多少回合

        """
        team = player.team
        memory = team.get_memory()
        allStatus = memory["status"]
        if len(allStatus) == 0:
            return False
        # TODO:
        #   还需要判断回合数是否超出一已知回合？
        for i in range( len(allStatus) - 1 ,
                        len(allStatus) - 1 - turns,
                        -1 ): # 逆序
            previousStatus = allStatus[i][player.id]
            if previousStatus is None:
                return False
            elif status not in previousStatus:
                return False
        else:
            return True


    def make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """

        # 假装先让对方以自己的想法决策
        #-------------------------------
        # 分析对方的行为，可以对下一步的行为作出指导
        #
        for oppPlayer in self._opponentTeam.players:
            oppPlayer.make_decision()



        action1 = action2 = Action.INVALID
        signal1 = signal2 = Signal.NONE

        action3 = action4 = Action.INVALID # 中间变量
        signal3 = signal4 = Signal.NONE    # 中间变量


        # 我方玩家单独决策
        #------------------------------
        # 了解个人真实想法
        #

        action1, _ = self._player1.make_decision()
        action2, _ = self._player2.make_decision()

        returnActions = [ action1, action2 ]


        # TODO: 强攻信号
        #-----------------
        # 如果一个队友和一个敌人纠缠，一个敌人和我都在进攻，并且在是僵持模式
        # 在一些情况下有可能会触发防御，这个时候发强攻信号，减小安全性的判断


        # TODO: 追击信号
        #------------------
        # 如果对方明着就是要来拆家，那么发动追击信号，不要老是等人家走到底线了再去追杀 ...
        #



        # 检查是否有队员处在僵持阶段
        #--------------------------
        # 1. 双方均在墙后僵持不前进因为
        #
        # TODO:
        #   乱破墙，然后防御模式写得又烂，等于送死 ...
        #
        # TODO:
        #   单人不要随便破墙，但是有条件的破墙还是可以的！
        #   如果两个人均被一个人牵制，那么完全可以来一个双人决策
        #
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (False and action == Action.STAY                                 # 当前回合处于等待状态
                and player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)  # 墙后有人造成的
                and player.has_status(Status.WAIT_FOR_MARCHING)       # 因此等待行军
                and not player.has_status(Status.DEFENSIVE) # 不要让防御性的队友随意破墙
                and not player.has_status(Status.REALODING) # 目前有弹药
                and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=2)
                ): # 上两回合也处于僵持状态

                # 触发的条件是一方隔墙，队友因为这两个人的僵持受到牵制
                #----------------------------------------------------
                teammate = player.battler.teammate
                teammateAction = returnActions[ 1 - idx ] # 队友
                if (#teammateAction == Action.STAY # 不一定需要，因为队友可能在努力拆外墙
                    True and teammate.has_status()
                    ):
                    pass


                # 准备破墙，留好后路
                #------------------
                action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_BRICK)
                if Signal.is_break(signal3):
                    continue

                if (signal3 == Signal.READY_TO_PREPARE_FOR_BREAK_BRICK
                    or signal3 == Signal.READY_TO_BREAK_BRICK
                    ): # 均为合适的行为
                    returnActions[idx] = action3 # 设置为凿墙动作


        # 主动打破重叠的信号
        #-------------------
        # 1. 很多时候只有主动打破重叠，才能制造机会！
        #
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (action == Action.STAY
                and player.has_status(Status.OVERLAP_WITH_ENEMY)  # 在等待敌人
                and not player.has_status(Status.REALODING)        # 确认一下有炮弹
                and self.has_status_in_previous_turns(player, Status.OVERLAP_WITH_ENEMY, turns=3)
                ): # 数个回合里一直在等待

                action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_OVERLAP)
                if Signal.is_break(signal3):
                    continue

                if signal3 == Signal.READY_TO_BREAK_OVERLAP:
                    returnActions[idx] = action3


        action1, action2 = returnActions

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

    @property
    def data(self):
        return self._data

    @property
    def globalData(self):
        return self._globalData

    @property
    def requests(self):
        return self._requests

    @property
    def responses(self):
        return self._responses


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


class Tank2Botzone(Botzone, metaclass=SingletonMeta):

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
        if self._data is not None:
            self._data = DataSerializer.deserialize(self._data)
        if self._globalData is not None:
            try:
                self._globalData = DataSerializer.deserialize(self._globalData)
            except Exception as e:
                self._globalData = None

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

        if not len(allBlueActions) == 0 and not len(allRedActions) == 0:
            b0, b1 = zip(*allBlueActions)
            r0, r1 = zip(*allRedActions)
            self._pastActions = { # { (side, id): [Action] }
                (0, 0): b0, (0, 1): b1,
                (1, 0): r0, (1, 1): r1,
            }

    def make_output(self, actions, stream=sys.stdout,
                    debug=None, data=None, globaldata=None):
        if data is not None:
            data = DataSerializer.serialize(data)
        if globaldata is not None:
            globaldata = DataSerializer.serialize(globaldata)
        super().make_output(stream, actions, debug, data, globaldata)

    def get_past_actions(self, side, id):
        """
        获得某一坦克的历史决策
        """
        return self._pastActions.get( (side, id), [] ) # 没有记录则抛出 []

#{ END 'botzone.py' }#



#{ BEGIN 'main.py' }#

def main(istream=None, ostream=None):

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT) # Singleton

    terminal = Tank2Botzone(map_, long_running=LONG_RUNNING_MODE) # Singleton

    istream = istream or BotzoneIstream()
    ostream = ostream or BotzoneOstream()

    while True:

        t1 = time.time()

        if LONG_RUNNING_MODE: # 这个模式下 map 对象会复用，首先需要重置
            map_.reset()

        terminal.handle_input(stream=istream)

        if SIMULATOR_ENV:
            map_.debug_print_out()

        if terminal.data is not None:
            memory = terminal.data["memory"]
        else:
            memory = {
                BLUE_SIDE: None,
                RED_SIDE: None,
            }

        side = terminal.mySide
        tanks = map_.tanks

        bluePlayer0 = Tank2Player(tanks[BLUE_SIDE][0], map_, terminal.get_past_actions(BLUE_SIDE, 0))
        bluePlayer1 = Tank2Player(tanks[BLUE_SIDE][1], map_, terminal.get_past_actions(BLUE_SIDE, 1))
        redPlayer0  = Tank2Player(tanks[RED_SIDE][0], map_, terminal.get_past_actions(RED_SIDE, 0))
        redPlayer1  = Tank2Player(tanks[RED_SIDE][1], map_, terminal.get_past_actions(RED_SIDE, 1))
        bluePlayers = [bluePlayer0, bluePlayer1]
        redPlayers  = [redPlayer0, redPlayer1]

        bluePlayer0.set_teammate(bluePlayer1)
        bluePlayer1.set_teammate(bluePlayer0)
        redPlayer0.set_teammate(redPlayer1)
        redPlayer1.set_teammate(redPlayer0)
        bluePlayer0.set_opponents(redPlayers)
        bluePlayer1.set_opponents(redPlayers)
        redPlayer0.set_opponents(bluePlayers)
        redPlayer1.set_opponents(bluePlayers)

        blueTeam = Tank2Team(BLUE_SIDE, bluePlayer0, bluePlayer1, map_)
        redTeam  = Tank2Team(RED_SIDE, redPlayer0, redPlayer1, map_)
        blueTeam.set_opponent_team(redTeam)
        redTeam.set_opponent_team(blueTeam)
        blueTeam.load_memory(memory[BLUE_SIDE])
        redTeam.load_memory(memory[RED_SIDE])

        if side == BLUE_SIDE:
            myPlayer0  = bluePlayer0
            myPlayer1  = bluePlayer1
            myPlayers  = bluePlayers
            myTeam     = blueTeam
            oppPlayers = redPlayers
            oppTeam    = redTeam
        elif side == RED_SIDE:
            myPlayer0  = redPlayer0
            myPlayer1  = redPlayer1
            myPlayers  = redPlayers
            myTeam     = redTeam
            oppPlayers = bluePlayers
            oppTeam    = blueTeam
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
            def _print_decision(actions, side, players):
                for id_, action in enumerate(actions):
                    simulator_print("%s %02d: %s \t[status] %s" % (
                        _SIDE_NAMES[side], id_+1, Action.get_name(action),
                        ", ".join( Status.get_name(status) for status in players[id_]._status ) ) )
            _print_decision(actions, side, myPlayers)
            _print_decision(oppActions, 1-side, oppPlayers)
            simulator_print(_CUT_OFF_RULE)
            simulator_print("Actually actions on this turn:")
            simulator_print(_CUT_OFF_RULE)
            for side, tanks in enumerate(map_.tanks):
                for id_, tank in enumerate(tanks):
                    simulator_print("%s %02d: %s" % (_SIDE_NAMES[side], id_+1,
                                        Action.get_name(tank.previousAction)))
            simulator_print(_CUT_OFF_RULE)


        t2 = time.time()

        data = {

            "memory": [
                blueTeam.dump_memory(),
                redTeam.dump_memory()
            ],

        }

        debugInfo = {

            "cost": round(t2-t1, 4),

            }

        terminal.make_output(actions, stream=ostream, debug=debugInfo, data=data)


if __name__ == '__main__':
    main()

#{ END 'main.py' }#



