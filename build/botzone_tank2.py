# -*- coding: utf-8 -*-
# @author:      Rabbit
# @filename:    botzone_tank2.py
# @date:        2019-05-29 21:31:38
# @site:        https://github.com/zhongxinghong/Botzone-Tank2
# @description: Automatically built Python single-file script for Botzone/Tank2 game
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
import types
import json
import random
import pickle
import base64
import gzip
import hashlib
import numpy as np
from collections import deque
from pprint import pprint
import functools
from contextlib import contextmanager
from copy import deepcopy

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


@contextmanager
def outer_label():
    """
    用于直接打断外层循环，或者继续外层循环

    如果置于循环体之外，就是 break outer
    如果置于循环体之内，就是 continue outer
    """
    class _GotoOuterException(Exception):
        pass
    try:
        yield _GotoOuterException() # 每次创建后都不相同，嵌套的情况下，需要确保名称不相同
    except _GotoOuterException:     #　这样做是为了防止嵌套的情况下，无法从内层直接跳到最外层
        pass

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


def memorize(func):
    """
    根据参数列表缓存函数的返回值的修饰器
    ------------------------------------

    1. func 会以 __memory__ 缓存返回结果
    2. func 会带上 make_key 方法，可以用来获取传入参数列表对应的缓存 key
    3. func 会带上 clear_memory 方法，可以清空所有的缓存结果
    4. 如果返回值是生成器，会立即获得完整结果并转为 tuple 类型


    这个函数主要用于缓存搜索路径

    """
    def _make_key(func, *args, **kwargs):
        _key = (
            func.__module__,
            func.__name__,
            args,
            sorted(kwargs.items()) # kwargs 自动排序
        )
        return hashlib.md5(pickle.dumps(_key)).hexdigest()

    def _clear_memory(func):
        if hasattr(func, "__memory__"):
            func.__memory__.clear()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(func, "__memory__"):
            func.__memory__ = {}
        key = _make_key(func, *args, **kwargs)
        res = func.__memory__.get(key, _MISSING)
        if res is _MISSING:
            res = func(*args, **kwargs)
            if isinstance(res, types.GeneratorType):
                res = list(res) # 如果返回结果是生成器，那么马上获得所有结果
            func.__memory__[key] = res
        return res

    wrapper.make_key = functools.partial(_make_key, func)
    wrapper.clear_memory = functools.partial(_clear_memory, func)

    return wrapper


class SingletonMeta(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:
            cls._instance[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
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


    class _Counter(object):
        """
        一个用于回滚计数的内部类
        """
        def __init__(self):
            self._counter = 0

        def increase(self):
            self._counter += 1

        def __iter__(self):
            return iter(range(self._counter))

        def __repr__(self):
            return self._counter.__repr__()

        def __int__(self):
            return self._counter


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
        self._performedActionsRecord = {} # turn -> [[int, int], [int, int]] 记录 perform 所执行过的动作，用于 undo_revert
        self._init_bases()
        self._init_tanks()
        # -----------------------
        #self._revertStack = [] # [debug] 保存需要 revert 的行为
        #self._revertIdx = 0 # [debug] 当前 revert 的编号


    def reset(self): # 重置整个地图
        self.__clean_cache()
        width, height = self.size
        self.__init__(width, height)

    def __clean_cache(self): # 清除缓存属性
        #CachedProperty.clean(self, "matrix")
        #CachedProperty.clean(self, "matrix_T")
        pass # 不再使用缓存啦

    @property
    def turn(self): # 当前回合数
        return self._turn

    @property
    def tanks(self):
        return self._tanks

    @property
    def bases(self):
        return self._bases

    #@CachedProperty # 缓存效果不明显
    @property
    def matrix(self):
        """
        缓存 to_type_matrix 的值

        WARNING:

            - 因为 list 是可变对象，因此不要对返回值进行修改，以免缓存的属性值改变
            - 如需修改，需要首先调用 np.copy(matrix) 获得一个副本，然后对副本进行修改
        """
        return self.to_type_matrix()

    #@CachedProperty # 缓存效果不明显
    @property
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
        #assert Action.is_move(action), "action %s is not a move-action" % action
        if not Action.is_move(action): # 因为模拟地图导致了一些不可测的结果，这个地方不能 assert
            return False               # 只要打一个补丁，开发的时候自己注意一下就好，记得 action % 4

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
        # assert Action.is_shoot(action), "action %s is not a shoot-action" % action
        if not Action.is_shoot(action):
            return False
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
        self._performedActionsRecord[self._turn] = _actions
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
                tank.previousAction = action # 缓存本次行为，不考虑坦克是否已经挂掉

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


    def single_simulate(self, tank, action):
        """
        模拟一回合：
            其中一架 tank 执行一个特定行为，其他 tank 均不动

        模拟结束后，会自动回滚

        Input:
            - tank     TankField/BattleTank   能表明坐标的 tank 对象
            - action   int                    下回合的行动

        """
        actions = [
            [Action.STAY for _ in range(TANKS_PER_SIDE) ] for __ in range(SIDE_COUNT)
        ]
        actions[tank.side][tank.id] = action
        self.perform(*actions)

    def multi_simulate(self, *actions):
        """
        模拟一回合：
            其中指定的多架坦克执行特定行为，其他 tank 均不动

        模拟结束后，会自动回滚

        Input:
            - *args   格式为 ( (Tank, action), (Tank, action), ... ) Tank 对象要求包含 side/id 属性

        """
        performedActions = [
            [Action.STAY for _ in range(TANKS_PER_SIDE) ] for __ in range(SIDE_COUNT)
        ]
        for tank, action in actions:
            performedActions[tank.side][tank.id] = action
        self.perform(*performedActions)

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


    def undo_revert(self):
        """
        从当前回合主动回滚到之前回合后，再将 revert 这个动作撤销
        """
        nextTurn = self._turn + 1
        assert nextTurn in self._performedActionsRecord, "no previously revert operation found"
        actions = self._performedActionsRecord[nextTurn]
        self.perform(*actions)


    @contextmanager
    def simulate_one_action(self, tank, action):
        """
        simulate 的 with 版用法，结束后会自动回滚
        """
        try:
            self.single_simulate(tank, action)
            #debug_print("simulate:", tank, action)
            #self._revertIdx += 1
            #self._revertStack.append( (self._revertIdx, tank, action) )

            yield

        except Exception as e:
            raise e
        finally:
            self.revert() # 不管出于什么错误，模拟结束后必定回滚
            #self._revertStack.pop()
            #debug_print("revert:", tank, action)

    @contextmanager
    def simulate_multi_actions(self, *actions):
        """
        multi_simulate 的 with 用法
        """
        try:
            self.multi_simulate(*actions)
            yield
        except Exception as e:
            raise e
        finally:
            self.revert()

    @contextmanager
    def rollback_to_previous(self):
        """
        回滚到先前回合

        回滚结束后，会自动撤销回滚

        """
        try:
            success = self.revert()
            yield
        except Exception as e:
            raise e
        finally:
            if success:
                self.undo_revert() # 回合结束后撤销回滚


    @contextmanager
    def auto_revert(self):
        """
        自动实现多轮回滚

        可以在 yield 后连续不定次调用 single_simulate/multi_simulate 函数，
        模拟结束后自动调用 counter 次 revert 来自动多轮回滚

        yield 后可以通过调用 cnt.increase 来增加回滚次数

        """
        try:
            cnt = self.__class__._Counter()
            yield cnt  # 每成功调用一次 map_.simulate 就需要调用一次 increase

        except Exception as e:
            raise
        finally:
            for _ in cnt:
                self.revert()


    @contextmanager
    def auto_undo_revert(self):
        """
        同上，但会在结束时通过调用 counter 次 undo_revert 来实现多轮 revert 操作的回滚
        """
        try:
            cnt = self.__class__._Counter()
            yield cnt  # 每成功调用一次 map_.revert 就需要调用一次 increase

        except Exception as e:
            raise
        finally:
            for _ in cnt:
                self.undo_revert()


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



#{ BEGIN 'tank.py' }#

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

    def is_this_field_in_our_site(self, field, include_midline=False):
        """
        判断某个 field 是否位于我方半边地盘

        Input:
            - field             Field
            - include_midline   bool    是否包含分界线

        """
        base = self._map.bases[self.side]
        if include_midline:
            return ( np.abs( field.y - base.y ) <= 4 )
        else:
            return ( np.abs( field.y - base.y ) < 4 )

    def is_this_field_in_enemy_site(self, field, include_midline=False): # 默认不包含中线
        """
        是否处于敌方半边的地图

        """
        return not self.is_this_field_in_our_site(field, include_midline= not include_midline)

    def is_in_our_site(self, include_midline=False):
        """
        是否处于我方半边的地图

        Input:
            - include_midline   bool   是否包含分界线

        """
        return self.is_this_field_in_our_site(self.tank, include_midline=include_midline)

    def is_in_enemy_site(self, include_midline=True):
        """
        是否处于地方半边的地图
        """
        return self.is_this_field_in_enemy_site(self.tank, include_midline=include_midline)

    def is_near_midline(self, offset=1):
        """
        是否在中线附近

        Input:
            - offset   int   定义中线范围为 4 ± offset 的范围
                             例如 offset = 1 则 [3, 5] 均为中线范围
        """
        return ( np.abs( self.y - 4 ) <= offset )


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

    def get_all_valid_move_actions(self, **kwargs):
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

    def get_all_valid_shoot_actions(self):
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
        return self.get_all_valid_move_actions() + self.get_all_valid_shoot_actions() + [ Action.STAY ]

    def get_all_shortest_attacking_routes(self, ignore_enemies=True, bypass_enemies=False, delay=0, **kwargs):
        """
        获得所有最短的进攻路线
        --------------------------

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

        kwargs.setdefault("middle_first", False) # 优先边路搜索

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


    def get_next_attacking_action(self, route=None):
        """
        下一个进攻行为，不考虑四周的敌人

        Input:
            - route   Route   自定义的攻击路径
                              默认为 None ，使用默认的最短路径
        """
        tank    = self._tank
        map_    = self._map
        oppBase = map_.bases[1 - tank.side]
        battler = self

        if route is None:
            route = battler.get_shortest_attacking_route()

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
                        if battler.canShoot: # 这个时候如果能够射击，就优先射击
                            return action + 4
                    else:
                        continue
            # 其他情况仍然优先移动
            return action

        ## 遇到墙/敌方基地/坦克，不能移动
        if battler.canShoot: # 尝试射击
            action += 4
            for field in battler.get_destroyed_fields_if_shoot(action):
                if isinstance(field, TankField) and field.side == tank.side:
                    return Action.STAY # 仅需要防止射到队友
            return action

        # 不能射击，只好等待
        return Action.STAY

    def get_all_next_attacking_actions(self, routes=None):
        """
        返回所有给定路线的下一回合行为的并集

        Input:
            - route   [Route]/None

        Return:
            - actions   [int]

        """
        if routes is None:
            routes = self.get_all_shortest_attacking_routes() # 默认用所有最短的进攻路线
        return list(set( self.get_next_attacking_action(route) for route in routes ))

    def get_all_shortest_defensive_routes(self, delay=0, **kwargs):
        """
        获得所有的回防路线
        ----------------

        同 get_all_shortest_attacking_routes

        """
        map_ = self._map
        tank = self._tank
        side = tank.side
        base = map_.bases[side]

        matrix_T = map_.matrix_T

        kwargs.setdefault("middle_first", True)

        routes = find_all_routes_for_move(
                        tank.xy,
                        base.xy,
                        matrix_T,
                        **kwargs,
                        )

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


    def get_shortest_defensive_route(self, *args, **kwargs):
        """
        获取默认的最短路线
        """
        for route in self.get_all_shortest_defensive_routes(*args, **kwargs):
            return route # 直接返回第一个


    def get_next_defensive_action(self, route=None):
        """
        获得下一个防御动作，不考虑周围敌人
        """
        tank = self._tank
        map_ = self._map
        base = map_.bases[tank.side]

        if route is None:
            route = self.get_shortest_defensive_route()

        if route.is_not_found():
            return Action.STAY
        elif route.length == 0:
            return Action.STAY

        x1, y1 = tank.xy
        x3, y3 = route[1].xy # 跳过 start
        action = Action.get_action(x1, y1, x3, y3) # move-action
        dx, dy = Action.DIRECTION_OF_ACTION_XY[action]

         ## 优先移动 ##
        if map_.is_valid_move_action(tank, action):
            return action

        ## 遇到墙/己方基地/坦克，不能移动
        if self.canShoot: # 尝试射击
            action += 4
            for field in self.get_destroyed_fields_if_shoot(action):
                if isinstance(field, TankField) and field.side == tank.side:
                    return Action.STAY # 仅需要防止射到队友
                elif isinstance(field, BaseField) and field is base:
                    return Action.STAY # 遇到己方基地
            return action

        # 否则就是等待了
        return Action.STAY


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


    def get_route_to_enemy_by_move(self, oppTank, block_teammate=True, **kwargs):
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

        # 优先左右拦截
        kwargs.setdefault("middle_first", True)
        kwargs.setdefault("x_axis_first", True)

        route = find_shortest_route_for_move(
                            tank.xy,
                            oppTank.xy,
                            map_.matrix_T,
                            block_types=block_types,
                            **kwargs,
                            )
        return route


    def get_route_to_point_by_move(self, x2, y2, **kwargs):
        """
        这个函数仅限于在基地中获得用来移动到两个 guard point 的最短路径 ！s
        """
        tank = self._tank
        map_ = self._map
        side = tank.side

        # 优先左右移动
        kwargs.setdefault("middle_first", True)
        kwargs.setdefault("x_axis_first", True)

        route = find_shortest_route_for_move(
                            tank.xy,
                            (x2, y2),
                            map_.matrix_T,
                            block_types=DEFAULT_BLOCK_TYPES+(
                                Field.BASE + 1 + side,
                            ),
                            **kwargs,
                            )

        return route


    def get_route_to_field_by_move(self, field, **kwargs):
        """
        上一个函数的一个简单扩展
        """
        x2, y2 = field.xy
        return self.get_route_to_point_by_move(x2, y2, **kwargs)


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


    def get_manhattan_distance_to_point(self, x2, y2):
        """
        对上一函数的补充，允许传入 xy 作为变量
        """
        x1, y1 = self.xy
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
        base = map_.bases[side]
        oppBase = map_.bases[1- side]
        teammate = map_.tanks[side][1 - tank.id]
        battler  = self

        x1, y1 = tank.xy
        x2, y2 = oppTank.xy
        if battler.is_in_our_site():
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

        #
        # 应该朝着远离队友的方向闪避？ 5ce915add2337e01c7abd895
        #
        # 因为 BUG ，这个功能尚未实现 5ce9ce0cd2337e01c7acfd5c
        #

        #
        # 我决定不删掉这里的任何一条 DEBUG 注释来纪念这个花了 5 个小时都没有搞懂的 BUG
        # 没有错，把下面这段全部注释掉，这个程序就一点 BUG 都没有了
        #
        '''def _cmp(action):
            #debug_print("Inner: ", id(map_), id(battler), id(teammate), id(action), action)
            #map_.debug_print_out()
            with map_.simulate_one_action(tank, action):
                #map_.debug_print_out()
                return battler.get_manhattan_distance_to(teammate)'''

        #debug_print("Before:", id(map_), id(battler), id(teammate), id(action), action)

        #map_.debug_print_out()
        #debug_print(teammate.previousAction)
        '''if battler.on_the_same_line_with(teammate): # 仅仅在处于同一行时成立
            #debug_print(actions)
            actions.sort(key=lambda action: _cmp(action), reverse=True)
            #debug_print(actions)'''
        #debug_print(teammate.previousAction, "\n") # 因为一些奇怪的原因，地图没有正确回滚！！
        #map_.debug_print_out()

        #debug_print("After: ", id(map_), id(battler), id(teammate), id(action), action)
        #debug_print("")

        ### END BUG ###

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


    def on_the_same_line_with(self, field, ignore_brick=True):
        """
        是否和某个块处在同一条直线上

        Input:
            field          任何带坐标的 tank 对象
            ignore_brick   bool    是否忽略土墙的阻挡

        """
        tank = self._tank
        map_ = self._map
        x1, y1 = tank.xy
        x2, y2 = field.xy

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
            _fields = map_[x, y]
            if len(_fields) == 0:
                continue
            elif len(_fields) == 2:
                if field.xy == (x, y): # 说明处在在多人坦克里
                    return True
                else: # 否则不算
                    return False
            else:
                _field = _fields[0]
                if _field.xy == field.xy: # 和这个块坐标相同（注意不要用 is 来判断，因为传入的可能是 BattleTank）
                    return True
                elif isinstance(_field, (EmptyField, WaterField) ):
                    continue
                elif isinstance(_field, BrickField):
                    if ignore_brick: # 这种情况将 brick 视为空
                        continue
                    else:
                        return False
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


    def will_destroy_a_brick_if_shoot(self, action):
        """
        如果当前回合射击，是否能够摧毁一个墙
        """
        destroyedFields = self.get_destroyed_fields_if_shoot(action)
        if len(destroyedFields) == 1:
            field = destroyedFields[0]
            if isinstance(field, BrickField):
                return True
        return False


    def is_face_to_enemy_base(self, ignore_brick=False):
        """
        是否直面对方基地，或者是与敌人基地处在同一条直线上 （一个历史遗留接口）

        Input:
            - ignore_brick   bool   是否忽略土墙，如果忽略，那么只需要基地和坦克
                                    处在同一直线上即可
        """
        oppBase = self._map.bases[1 - self.side]
        return self.on_the_same_line_with(oppBase, ignore_brick=ignore_brick)


    def is_closest_to(self, field, allow_diagonal=True):
        """
        是否紧贴某个 field 也就是与之相邻或恰为对角

        Input:
            - field            Field   事实上只要带有 xy 属性的类都可以
            - allow_diagonal   bool    是否将对角线关系也算入

        """
        x1, y1 = self.xy
        x2, y2 = field.xy
        isInnermost = ( np.abs(x1 - x2) <= 1 and np.abs(y1 - y2) <= 1 )
        if allow_diagonal:
            return isInnermost
        else:
            return isInnermost and (x1 == x2 or y1 == y2) # 还需要共线


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
                    route1 = self.get_route_to_enemy_by_move(enemy)
                    if route1.is_not_found():
                        route1 = self.get_route_to_enemy_by_move(enemy, block_teammate=False)
                        if route1.is_not_found(): # 我无法到达敌人的位置？？？
                            continue
                    route2 = teammateBattler.get_route_to_enemy_by_move(enemy)
                    if route2.is_not_found():
                        route2 = teammateBattler.get_route_to_enemy_by_move(enemy, block_teammate=False)

                    if route2.is_not_found():
                        deltaLength = route1.length # 这样做是否合理？
                    else:
                        deltaLength = route1.length - route2.length
                    deltaLengthWithEnemyList.append( (deltaLength, enemy) )
                    idx = deltaLengthWithEnemyList.index(
                                    min(deltaLengthWithEnemyList, key=lambda tup: tup[0]) )
                    return deltaLengthWithEnemyList[idx][1]


        # 否则为单人决策

        routes = [ self.get_route_to_enemy_by_move(enemy) for enemy in enemies ]

        if all( route.is_not_found() for route in routes ): # 均不可到达？
            routes = [ self.get_route_to_enemy_by_move(enemy, block_teammate=False)
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

    def get_enemy_delay_if_bypass_me(self, oppBattler):
        """
        假设自己不移动，敌人必须要饶过我，那么他将因此延迟多少步

        """
        route1 = oppBattler.get_shortest_attacking_route(ignore_enemies=True, bypass_enemies=False)
        route2 = oppBattler.get_shortest_attacking_route(ignore_enemies=False, bypass_enemies=True)

        if route1.is_not_found(): # TODO: 如何处理本来就找不到路的情况?
            return INFINITY_ROUTE_LENGTH

        if route2.is_not_found():
            return INFINITY_ROUTE_LENGTH

        delay = route2.length - route1.length
        assert delay >= 0 # 显然必定会大于 0 ！

        return delay


    def can_block_this_enemy(self, oppBattler):
        """
        假设自己不移动，对方将不得不绕路，或者他将因此无路可走，那么就算是成功堵住了他

        """
        delay = self.get_enemy_delay_if_bypass_me(oppBattler)
        if delay == INFINITY_ROUTE_LENGTH: # 让敌人根本无路可走
            return True
        return (delay >= 2) # 造成两步步以上的延迟，那么就算堵路成功

#{ END 'tank.py' }#



#{ BEGIN 'strategy/signal.py' }#

class Signal(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 200

    INVALID     = -1  # 无效信号
    NONE        = 0   # 空信号
    UNHANDLED   = 1   # 未处理团队信号，通常是因为有更紧急的状况而没有运行到相应的处理信号的位置
    CANHANDLED  = 2   # 未能处理团队信号，通常是因为尝试处理但是发现不合适


    PREPARE_FOR_BREAK_BRICK          = 11  # 团队信号，准备破墙，先给自己寻找后路
    READY_TO_PREPARE_FOR_BREAK_BRICK = 12  # 队员信号，准备好为破墙而凿开两边墙壁

    FORCED_TO_BREAK_BRICK            = 13  #　团队信号，强制破墙
    READY_TO_BREAK_BRICK             = 14  # 队员信号，准备要破墙

    SUGGEST_TO_BREAK_OVERLAP         = 15  # 团队信号，建议马上打破重叠
    READY_TO_BREAK_OVERLAP           = 16  # 队员信号，准备要主动打破重叠

    FORCED_MARCH                     = 17  # 团队信号，强制行军
    READY_TO_FORCED_MARCH            = 18  # 队员信号，准备强制行军

    SHOULD_LEAVE_TEAMMATE            = 19  # 团队信号，需要和队友打破重叠
    READY_TO_LEAVE_TEAMMATE          = 20  # 队员信号，准备和队友打破重叠

    SUGGEST_TO_BACK_AWAY_FROM_BRICK  = 21  # 团队信号，建议反向远离墙壁
    READY_TO_BACK_AWAY_FROM_BRICK    = 22  # 队员信号，准备反向远离墙壁


    @staticmethod
    def is_break(signal):
        """
        该信号是否意味着沟通停止
        也就是是否为未处理或无法处理

        """
        return signal in (

                __class__.INVALID,
                __class__.UNHANDLED,
                __class__.CANHANDLED,

                )

#{ END 'strategy/signal.py' }#



#{ BEGIN 'strategy/status.py' }#

class Status(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 100

    NONE       = 0  # 空状态

    AGGRESSIVE = 1  # 侵略性的
    STALEMENT  = 2  # 僵持的
    DEFENSIVE  = 3  # 防御性的
    WITHDRAW   = 4  # 撤退性的
    DYING      = 5  # 准备要挂了
    DIED       = 6  # 已经挂了
    RELOADING  = 9  # 正在装弹，下回合无法射击

    ENCOUNT_ENEMY                    = 17  # 遇到敌人
    ENCOUNT_ONE_ENEMY                = 18  # 遇到一个敌人
    ENCOUNT_TWO_ENEMY                = 19  #　遇到两个敌人
    OVERLAP_WITH_ENEMY               = 20  # 正在和敌人重叠
    KEEP_ON_MARCHING                 = 21  # 继续行军
    READY_TO_ATTACK_BASE             = 22  # 准备拆基地
    READY_TO_FIGHT_BACK              = 23  # 准备反击
    READY_TO_DODGE                   = 24  # 准备闪避敌人
    READY_TO_KILL_ENEMY              = 25  # 准备击杀敌人
    READY_TO_BLOCK_ROAD              = 26  # 准备堵路
    KEEP_ON_OVERLAPPING              = 27  # 等待与自己重叠的敌人的决策
    WAIT_FOR_MARCHING                = 28  # 存在风险，等待进攻
    HAS_ENEMY_BEHIND_BRICK           = 29  # 隔墙有人
    PREVENT_BEING_KILLED             = 30  # 为了防止被射击而停下
    HUNTING_ENEMY                    = 31  # 主动追杀敌军
    ACTIVE_DEFENSIVE                 = 32  # 主动防御状态
    WILL_DODGE_TO_LONG_WAY           = 33  # 遭遇敌人自己没有炮弹，为了保命而闪避，但是增加了攻击路线长度
    OPPOSITE_SHOOTING_WITH_ENEMY     = 34  # 正在和敌人对射
    READY_TO_BACK_AWAY               = 35  # 假装逃跑
    READY_TO_CLEAR_A_ROAD_FIRST      = 36  # 进攻时预先清除与自己相隔一步的土墙
    READY_TO_DOUBLE_KILL_ENEMIES     = 37  # 遇到敌人重叠在一起，尝试和两个敌人同归于尽
    READY_TO_LEAVE_TEAMMATE          = 38  # 准备和队友打破重叠
    FACING_TO_ENEMY_BASE             = 39  # 正面敌人基地，或者和敌人基地处在同一直线上
    READY_TO_FOLLOW_ENEMY            = 40  # 准备跟随墙后敌人的移动方向
    READY_TO_WITHDRAW                = 41  # 准备后撤
    GRARD_OUR_BASE                   = 42  # 已经到达我方基地附近，进入守卫状态
    STAY_FOR_GUARDING_OUR_BASE       = 43  # 已经到达我方基地附近，准备停留等待
    WAIT_FOR_WITHDRAWING             = 44  # 等待回防，可能是由于敌人阻挡
    MOVE_TO_ANOTHER_GUARD_POINT      = 45  # 向着另一个 guard point 移动
    ENEMY_MAY_APPEAR_BEHIND_BRICK    = 46  # 也许会有敌人出现在墙后
    READY_TO_CUT_THROUGH_MIDLINE     = 47  # 墙后停止不前时，准备打通中线
    TRY_TO_BREAK_ALWAYS_BACK_AWAY    = 48  # 尝试打破一直回头的状态
    FORCED_MARCHING                  = 49  # 强制行军，强攻，不考虑某些可能的风险
    FORCED_WITHDRAW                  = 50  # 强制撤退，不考虑可能的风险
    READY_TO_PREPARE_FOR_BREAK_BRICK = 51  # 准备为破墙而准备闪避路线
    READY_TO_BREAK_BRICK             = 52  # 准备破墙
    READY_TO_BREAK_OVERLAP           = 53  # 准备主动打破重叠
    READY_TO_FORCED_MARCH            = 54  # 准备主动强攻
    FORCED_STOP_TO_PREVENT_TEAM_HURT = 55  # 防止团队间相互攻击而强制停止
    READY_TO_BACK_AWAY_FROM_BRICK    = 56  # 准备主动反向远离墙壁
    HELP_TEAMMATE_ATTACK             = 57  # 合作拆家，并且帮助队友进攻
    ATTEMPT_TO_KILL_ENEMY            = 58  # 主动防御时，尝试击杀敌军，这个状态可以用来记忆行为
    BLOCK_ROAD_FOR_OUR_BASE          = 59  # 主动防御时，遇到敌方面向基地，但没有炮弹，自己又恰好能阻挡在中间
    SACRIFICE_FOR_OUR_BASE           = 60  # 主动防御时，遇到敌方下一炮打掉基地，自己又恰好能阻挡


    __Status_Name_Cache = None

    @staticmethod
    def get_name(status):
        """
        通过状态值自动判定方法
        """
        if __class__.__Status_Name_Cache is None:
            cache = __class__.__Status_Name_Cache = {}
            for k, v in __class__.__dict__.items():
                if not k.startswith("_"):
                    if isinstance(v, int):
                        key = k.title()
                        cache[v] = key
        cache = __class__.__Status_Name_Cache
        return cache.get(status, None) # 应该保证一定有方法？

#{ END 'strategy/status.py' }#



#{ BEGIN 'strategy/label.py' }#

class Label(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 300

    NONE = 0

    BREAK_OVERLAP_SIMULTANEOUSLY          = 1  # 会和我同时打破重叠
    SIMULTANEOUSLY_SHOOT_TO_BREAK_OVERLAP = 2  # 回合我方同时以射击的方式打破重叠
    IMMEDIATELY_BREAK_OVERLAP_BY_MOVE     = 3  # 当敌人和我方坦克重叠时，对方立即与我打破重叠
    KEEP_ON_WITHDRAWING                   = 4  # 我方坦克持久化撤退状态
    DONT_WITHDRAW                         = 5  # 强制性要求一个队员不再防御
    ALWAYS_BACK_AWAY                      = 6  # 我方坦克总是尝试回头


    __Status_Name_Cache = None

    @staticmethod
    def get_name(status):
        """
        通过状态值自动判定方法
        """
        if __class__.__Status_Name_Cache is None:
            cache = __class__.__Status_Name_Cache = {}
            for k, v in __class__.__dict__.items():
                if not k.startswith("_"):
                    if isinstance(v, int):
                        key = k.title()
                        cache[v] = key
        cache = __class__.__Status_Name_Cache
        return cache.get(status, None) # 应该保证一定有方法？

#{ END 'strategy/label.py' }#



#{ BEGIN 'strategy/utils.py' }#

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
        if (cMatrixMap[oppTank.xy] == Field.TANK + 1 + oppSide
            or cMatrixMap[oppTank.xy] == Field.MULTI_TANK # 还需要考虑重叠的坦克
            ):
            cMatrixMap[oppTank.xy] = Field.EMPTY
    return cMatrixMap


def fake_map_matrix_T_thinking_of_enemy_as_steel(map, mySide):
    """
    伪造一个敌方坦克视为钢墙的地图类型矩阵
    用于在堵路时估计对方时候存在绕路的可能
    """
    map_ = map
    oppSide = 1 - mySide
    cMatrixMap = map_.matrix_T.copy()
    for oppTank in map_.tanks[oppSide]:
        if (cMatrixMap[oppTank.xy] == Field.TANK + 1 + oppSide
            or cMatrixMap[oppTank.xy] == Field.MULTI_TANK # 还需要考虑重叠的坦克
            ):
            cMatrixMap[oppTank.xy] = Field.STEEL
    return cMatrixMap


def get_manhattan_distance(x1, y1, x2, y2):
    """
    获得 (x1, y1) -> (x2, y2) 曼哈顿距离
    """
    return np.abs(x1 - x2) + np.abs(y1 - y2)

#{ END 'strategy/utils.py' }#



#{ BEGIN 'strategy/route.py' }#

INFINITY_WEIGHT       = -1 # 无穷大的权重，相当于不允许到达
INFINITY_ROUTE_LENGTH = -1 # 无穷大的路径长度，相当于找不到路径

DUMMY_ACTION = -2 # 空行为
NONE_ACTION  = -1 #　上回合什么都不做，相当于停止，专门用于 start == end 的情况
MOVE_ACTION  = 0  # 上一回合操作标记为搜索
SHOOT_ACTION = 1  # 上一回合操作标记为射击

NONE_POINT = (-1, -1) # 没有相应的坐标


class RouteNode(object):
    """
    路径节点
    -----------------
    搜索得到路径后，用于对路径的节点进行对象化的描述

    Property:
        - x               int          坐标 x
        - y               int          坐标 y
        - xy              (int, int)   坐标 (x, y)
        - weight          int          节点权重，相当于走过这个节点需要多少步
        - arrivalAction   int          通过什么方式到达这个节点的

    """
    def __init__(self, x, y, weight=1, arrival_action=DUMMY_ACTION):
        self._x = x
        self._y = y
        self._weight = weight
        self._arrivalAction = arrival_action

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def xy(self):
        return (self._x, self._y)

    @property
    def weight(self):
        return self._weight

    @property
    def arrivalAction(self):
        return self._arrivalAction

    def from_shooting_area(self):
        return self._arrivalAction == SHOOT_ACTION

    def from_moving_area(self):
        return self._arrivalAction == MOVE_ACTION

    def __repr__(self):
        return str( (self._x, self._y, self._weight, self._arrivalAction) )

    def __copy__(self):
        return self

    def __deepcopy__(self):
        return RouteNode(self._x, self._y, self._weight, self._arrivalAction)


class Route(object):
    """
    路径类
    -----------------
    用于对搜索得到的路径进行对象化的描述

    Property:
        - nodes    [RouteNode]   从 start -> end 的节点链
        - length   int           路径长度
        - start    (x, y)        起点坐标
        - end      (x, y)        终点坐标

    Method:
        - is_not_found
        - has_block

    """
    def __init__(self, node_chain=None):
        """
        Input:
        ------------------------------------
        - node_chain    节点链的 head ，对应着最后一步到达的节点
                        其中的节点是符合如下结构的 list

                        def struct Node: [
                            "xy":     (int, int)          目标节点
                            "parent": Node/None           父节点
                            "step":   int ( >= 0 )        还差几步到达，为 0 表示到达，初始值为 weight - 1
                            "weight": const int ( >= 1 )  权重，即搜索时需要在其上耗费的步数
                            "last_action": const int      通过什么操作到达这个节点，该情况为移动
                        ]
        """
        self._nodeChain = self._get_dummy_head(node_chain) # 添加一个 dummy head 用于遍历


    @staticmethod
    def _get_dummy_head(head=None):
        """
        添加在原始 node chain head 前的 dummy head ，方便遍历
        """
        return [
            NONE_POINT,
            head, #　指向路径终点 end
            -1,
            -1,
            DUMMY_ACTION,
            ]

    @CachedProperty
    def nodes(self):
        nodes = []
        currentNode = self._nodeChain
        while True:
            currentNode = currentNode[1]
            if currentNode is not None:
                x, y   = currentNode[0]
                weight = currentNode[3]
                action = currentNode[4]
                nodes.append( RouteNode(x, y, weight, action) )
            else:
                break
        nodes.reverse()
        return nodes

    def is_not_found(self):
        """
        是否是空路径，即没有找到可以到达终点的路径
        """
        return ( len(self.nodes) == 0 )

    @CachedProperty
    def length(self):
        """
        获得路径长度，相当于节点权重的加和
        如果没有找到路线，那么返回 INFINITY_ROUTE_LENGTH
        """
        if self.is_not_found():
            return INFINITY_ROUTE_LENGTH
        return np.sum( node.weight for node in self.nodes )

    @property
    def start(self):
        """
        路径起点
        如果没有找到路径，那么返回 NONE_POINT
        """
        if self.is_not_found():
            return NONE_POINT
        return self.nodes[0].xy

    @property
    def end(self):
        """
        路径终点
        如果没有找到路径，那么返回 NONE_POINT
        """
        if self.is_not_found():
            return NONE_POINT
        return self.nodes[-1].xy

    def has_block(self, field):
        """
        判断一个 block 类型的 field (Brick/Base/Tank) 是否在该路径上
        所谓的 block 类型指的是：必须要射击一次才能消灭掉
        """
        assert isinstance(field, (BrickField, BaseField, TankField) ), "%r is not a block field" % field
        for node in self.nodes:
            if node.xy == field.xy:
                if node.weight >= 2 and node.arrivalAction == MOVE_ACTION: # 移动受阻
                    return True
                elif node.weight >= 1 and node.arrivalAction == SHOOT_ACTION: # 射击受阻
                    return True
        return False

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        return self.nodes[idx]

    def __iter__(self):
        yield from self.nodes

    def __contains__(self, xy):
        assert isinstance(xy, tuple) and len(xy) == 2, "(x, y) is required"
        for node in self.nodes:
            if node.xy == xy:
                return True
        return False

    def __repr__(self):
        return "Route(%s)" % self.nodes

    def __copy__(self):
        return self

    def __deepcopy__(self):
        return Route(deepcopy(self._nodeChain))

#{ END 'strategy/route.py' }#



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


def get_searching_directions(x1, y1, x2=None, y2=None, x_axis_first=False,
                             middle_first=False):
    """
    获得从 (x1, y1) -> (x2, y2) 最优的搜索方向顺序

    Input:
        - (x1, y1)   起点坐标
        - (x2, y2)   终点坐标，可以没有，那么将通过 (x1, y1) 在地图中的相对位置，
                     对应着左上、左下、右上、右下四个区域，确定最佳的搜索顺序

        - x_axis_first   bool   是否采用 x 轴方向优先的搜索方式。默认以垂直方向优先，
                                也就是如果存在到达目标坐标的两条长度相同的路径，
                                会优先从 y 轴方向移动过去，即先上下移动，后左右移动。
                                若选择以水平方向优先，则先左右移动，后上下移动。

                                优先上下移动通常用于侵略，优先左右移动通常用于防御

        - middle_first   bool   是否采用中路优先的搜索方式。默认不采用，而是优先从边路
                                搜索，如果边路和中路有距离相等的路径，那么优先从边路
                                走，如果中路发生冲突，就可以减小被敌人牵制的概率

        注： x 轴优先仅仅在中路优先的成立下才有意义，如果是旁路搜索，则对 x 轴优先的
            设置是无效的

    """
    if x2 is None or y2 is None: # 如果 x2, y2 为空，则默认以地图中点作为目标
        x2 = MAP_WIDTH  // 2
        y2 = MAP_HEIGHT // 2

    if   ( x2 - x1 >= 0 ) and ( y2 - y1 >= 0 ):
        if middle_first:
            return DIRECTIONS_DRUL if not x_axis_first else DIRECTIONS_RDLU
        else:
            return DIRECTIONS_LDRU
    elif ( x2 - x1 >= 0 ) and ( y2 - y1 <= 0 ):
        if middle_first:
            return DIRECTIONS_URDL if not x_axis_first else DIRECTIONS_RULD
        else:
            return DIRECTIONS_LURD
    elif ( x2 - x1 <= 0 ) and ( y2 - y1 >= 0 ):
        if middle_first:
            return DIRECTIONS_DLUR if not x_axis_first else DIRECTIONS_LDRU
        else:
            return DIRECTIONS_RDLU
    elif ( x2 - x1 <= 0 ) and ( y2 - y1 <= 0 ):
        if middle_first:
            return DIRECTIONS_ULDR if not x_axis_first else DIRECTIONS_LURD
        else:
            return DIRECTIONS_RULD

    raise Exception


def _BFS_search_all_routes_for_move(start, end, map_matrix_T, weight_matrix_T,
                                    block_types=DEFAULT_BLOCK_TYPES, x_axis_first=False,
                                    middle_first=False):
    """
    BFS 搜索从 start -> end 的所有路径路径，由短到长依次返回
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

        - middle_first      bool        是否采用中路优先的搜索

    Yield From:

        - routes            [Route]     所有可以到达的路径。如果没有搜索到可以到达的路径，则返回空路径

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

    # debug_print("map:\n", matrixMap.T)
    # debug_print("weight:\n", matrixWeight.T)
    # debug_print("can move on:\n", matrixCanMoveTo.astype(np.int8).T)

    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION,
        ]

    queue = deque() # queue( [Node] )
    matrixMarked = np.zeros_like(matrixMap, dtype=np.bool8)

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init

    _foundRoute = False

    while len(queue) > 0:

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if (x, y) == end: # 到达终点
            _foundRoute = True
            yield Route(node)
            continue

        if matrixMarked[x, y]:
            continue
        matrixMarked[x, y] = True

        if DEBUG_MODE:
            matrixDistance[x, y] = _get_route_length_by_node_chain(node)

        for dx, dy in get_searching_directions(x1, x2, y1, y2,
                                               x_axis_first=x_axis_first,
                                               middle_first=middle_first):
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
                MOVE_ACTION,
                ])
    '''
    if DEBUG_MODE:
        debug_print("distance matrix:\n", matrixDistance.T)
    '''

    if not _foundRoute:
        yield Route() # 空节点


def _BFS_search_all_routes_for_shoot(start, end, map_matrix_T, move_weight_matrix_T,
                                     shoot_weight_matrix_T, block_types=DEFAULT_BLOCK_TYPES,
                                     destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                                     x_axis_first=False, middle_first=False):
    """
    BFS 搜索从 start 开始到击中 end 的所有路径，由短到长依次返回
    ----------------------------------------------------------------------------

    实现思路：

    通过射击的方式能够比单纯通过移动的方式更快地接近目标，这是显而易见的，毕竟炮弹可以飞行。
    于是，将地图划分为两个区域，一个是可以发动射击的区域，它们仅仅与目标处在同一行或同一列的位置上
    另一个就是常规的移动可达的区域。搜索过程中对着两种情况下相应的节点权重做区分对待即可。

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

        - middle_first          bool    是否采用中路优先的搜索

    Yield From:

        - routes            [Route]     所有可以到达的路径。如果没有搜索到可以到达的路径，则返回空路径

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
    for dx, dy in get_searching_directions(x1, y1, x2, y2,
                                           x_axis_first=x_axis_first,
                                           middle_first=middle_first):
        x, y = end
        while True:
            x += dx
            y += dy
            if not (0 <= x < width and 0 <= y < height):
                break
            elif matrixMap[x, y] == Field.EMPTY: # 空对象
                pass
            elif matrixMap[x, y] == Field.WATER:
                continue # 水路不可以发动射击，但是可以射过去
            elif not matrixCanBeDestroyed[x, y] and (x, y) != start:
                break # 打一个补丁，不管怎么样，攻击者原地是可以发动射击的 ...
            matrixCanShoot[x, y] = True
            if (x, y) == start: # 已经找到了 start 没有必要再继续找下去了
                break

    # debug_print("map:\n", matrixMap.T)
    # debug_print("weight of move:\n", matrixMoveWeight.T)
    # debug_print("weight of shoot:\n", matrixShootWeight.T)
    # debug_print("can move to:\n", matrixCanMoveTo.astype(np.int8).T)
    # debug_print("can shoot:\n", matrixCanShoot.astype(np.int8).T)
    # debug_print("can be destroyed:\n", matrixCanBeDestroyed.astype(np.int8).T)


    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION, # 对于 start == end 的情况，将返回 startNode，相当于原地等待
        ]

    queue = deque() # queue( [Node] )
    matrixMarked  = np.zeros_like(matrixMap, dtype=np.bool8) # 标记移动到的位置

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init

    _foundRoute = False

    while len(queue) > 0:

        # if start == (8, 1):
        #     debug_print(start)
        #     debug_print([n[0] for n in queue])

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if (x, y) == end:
            _foundRoute = True
            yield Route(node)
            continue

        # 1. 如果当前处在射击区域
        # 2. 或者上回合射击（事实上射击行为必定是可延续的，也就是上回合 canShoot 这回合
        # 必定应该继续 canShoot ，但是对于 WaterField 来说，不属于可以发动射击的区域
        # 因此，如果上回合射进 WaterField 那么上一个判定条件就会失效。但在这种情况下
        # 应该视为射击行为延续，因此需要第二个判定条件）
        #
        if matrixCanShoot[x, y] or node[4] == SHOOT_ACTION:

            # 因为在射击区域中，行为的方向都是单向的，不会出现从射击区域进入移动区域，
            # 或者从射击的下一步移动回到上一步的情况，
            # 因此没有必要对射击行为已到达过的节点位置进行检查和标记

            if DEBUG_MODE:
                matrixDistance[x, y] = _get_route_length_by_node_chain(node)

            # 确定射击方向
            dx = np.sign(x2 - x)
            dy = np.sign(y2 - y)
            x3 = x + dx
            y3 = y + dy

            weight = matrixShootWeight[x3, y3]

            nextNode = [  # 必定可以保证下一个节点仍然处在射击区域，不会到达地图外，
                (x3, y3), # 并且下次还会继续进入这个分支，除非已经到达基地
                node,
                weight-1, # 补偿
                weight,
                SHOOT_ACTION, # 标志着上一步处在射击区域内
                ]

            if weight == 0: # 射击的过渡动作，下一个动作和当前动作同时发生
                queue.appendleft(nextNode) # 添加到开头，下回合马上继续
            else:
                queue.append(nextNode)

        else: # 否则为非射击区域，属于常规移动区域

            if matrixMarked[x, y]: # 只对移动区域进行标记
                continue
            matrixMarked[x, y] = True

            if DEBUG_MODE:
                matrixDistance[x, y] = _get_route_length_by_node_chain(node)

            for dx, dy in get_searching_directions(x1, y1, x2, y2,
                                                   x_axis_first=x_axis_first,
                                                   middle_first=middle_first):
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
                    MOVE_ACTION, # 标志着上一步处在非射击区域内
                    ])

    if not _foundRoute:
        yield Route() # 空节点


@memorize
def find_all_routes_for_move(start, end, matrix_T,
                             block_types=DEFAULT_BLOCK_TYPES,
                             x_axis_first=False, middle_first=False):
    """
    搜索移动到目标的所有路径

    Input:
        - matrix_T   np.array( [[int]] )   游戏地图的类型矩阵的转置

    Yield From:
        - route      Route
    """
    matrixMap = matrix_T

    matrixWeight = np.ones_like(matrixMap)
    matrixWeight[matrixMap == Field.BRICK] = 1 + 1 # 射击一回合，移动一回合
    matrixWeight[matrixMap == Field.STEEL] = INFINITY_WEIGHT
    matrixWeight[matrixMap == Field.WATER] = INFINITY_WEIGHT

    routes = _BFS_search_all_routes_for_move(
                    start, end, matrixMap, matrixWeight, block_types=block_types,
                    x_axis_first=x_axis_first, middle_first=middle_first)

    yield from routes


@memorize
def find_all_routes_for_shoot(start, end, matrix_T,
                              block_types=DEFAULT_BLOCK_TYPES,
                              destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                              x_axis_first=False,
                              middle_first=False):
    """
    搜索移动并射击掉目标的所有路径

    输入输出同上
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

    routes = _BFS_search_all_routes_for_shoot(
                    start, end, matrixMap, matrixMoveWeight, matrixShootWeight,
                    block_types=block_types, destroyable_types=destroyable_types,
                    x_axis_first=x_axis_first, middle_first=middle_first)

    yield from routes


def find_shortest_route_for_move(*args, **kwargs):
    """
    搜索移动到目标的最短路径
    """
    for route in find_all_routes_for_move(*args, **kwargs):
        return route # 直接返回第一个 route


def find_shortest_route_for_shoot(*args, **kwargs):
    """
    搜索移动并射击掉目标的最短路径
    """
    for route in find_all_routes_for_shoot(*args, **kwargs):
        return route # 直接返回第一个 route


def _get_route_length_by_node_chain(node):
    """
    [DEBUG] 传入 node chain head ，计算其所代表的节点链对应的距离

    Return:
        - length   int   路线长度，如果是空路线，返回 无穷大长度

    """
    assert isinstance(node, list) and len(node) == 5

    dummyHead = [
        NONE_POINT,
        node,
        -1,
        -1,
        DUMMY_ACTION,
        ]

    route = []
    node = dummyHead
    while True:
        node = node[1]
        if node is not None:
            x, y   = node[0]
            weight = node[3]
            route.append( (x, y, weight) )
        else:
            break

    if len(route) == 0:
        return INFINITY_ROUTE_LENGTH

    return np.sum( r[2] for r in route )

#{ END 'strategy/search.py' }#



#{ BEGIN 'strategy/evaluate.py' }#

def evaluate_aggressive(battler, oppBattler, strict=False, allow_withdraw=True):
    """
    根据敌我两架坦克的攻击线路长短，衡量当前侵略性

    Input:
        - battler           BattleTank
        - oppBattler        BattleTank
        - strict            bool   是否严格依据路线长度和两方基地位置进行评估
                                   如果为 False ，则还会考虑其他的因素
        - allow_withdraw    bool   是否允许撤退

    Return:
        [status]
        - Status.AGGRESSIVE   我方处于攻击状态
        - Status.DEFENSIVE    我方处于防御状态
        - Status.STALEMENT    双方处于僵持状态
        - Status.WITHDRAW     我方处于撤退状态
    """
    map_ = battler._map
    BattleTank = type(battler)

    myRoute = battler.get_shortest_attacking_route()
    oppRoute = oppBattler.get_shortest_attacking_route()

    # 可能会遇到这种糟糕的情况，队友挡住了去路 5cdde41fd2337e01c79f1284
    #--------------------------
    if myRoute.is_not_found() or oppRoute.is_not_found():
        return Status.AGGRESSIVE # 应该可以认为是侵略吧


    # assert not myRoute.is_not_found() and not oppRoute.is_not_found(), "route not found"
    leadingLength = oppRoute.length - myRoute.length

    #debug_print(battler, oppBattler, "leading:", leadingLength)

    if battler.is_in_enemy_site(): # 在敌方半边地图，更倾向于不防御

        if leadingLength >= 1:
            status = Status.AGGRESSIVE
        elif leadingLength < -3:
            status = Status.DEFENSIVE
        else:
            status = Status.STALEMENT

    else:
        #
        # 在我方半边地盘，会增加防御的可能性
        # 差一步都要算作防御！
        #
        if leadingLength >= 1:
            status = Status.AGGRESSIVE # [1, +)
        elif -1 < leadingLength < 1:
            status = Status.STALEMENT  # (-1, 1) -> 0
        elif -2 <= leadingLength <= -1:
            status = Status.DEFENSIVE  # [-2, -1]
        else:
            if allow_withdraw and battler.is_in_our_site(include_midline=True): # 包含中线，放松一点条件
                status = Status.WITHDRAW   # (-, -2)
            else:
                status = Status.DEFENSIVE # 否则不要撤退？

    if strict: # 严格模式直接返回评估状态
        return status

    #
    # 撤退性状态直接返回
    #
    if status == Status.WITHDRAW:
        return status

    #
    # 尽可能用攻击性策略！
    #
    # 还要判断对方的攻击路线是否可能会被我方队员阻拦
    # 否则就过度防御了 5ce69a15d2337e01c7a90646
    #
    if status != Status.AGGRESSIVE:
        map_ = battler._map
        tank = battler.tank
        teammate = None
        for _tank in map_.tanks[tank.side]:
            if _tank is not tank:
                teammate = _tank
                break

        if not teammate.destroyed:
            teammateBattler = BattleTank(teammate)
            for action in teammateBattler.get_all_valid_move_actions() + [ Action.STAY ]:
                with map_.simulate_one_action(teammateBattler, action):
                    if teammateBattler.xy in oppRoute:  # 此时视为侵略模式
                        return Status.AGGRESSIVE

    return status


def estimate_route_similarity(route1, route2):
    """
    评估两条路线的相似度
    一般用于判断选择某条路线是否可以和敌人相遇

    实现思路：
    --------------
    首先找出两者中最短的一条路径，对于其上每一个点，在另一条路上寻找与之距离最短（曼哈顿距离即可）
    的点，并将这两个点之间的距离作为总距离的一个部分，每个分距离和相应点的权重的加权平均值即为总距离

    最后的估值为 总距离除以最短路线的坐标点数的均值 的倒数
    值越接近 1 表示越相近，值越接近 0 表示越不相近

    根据实际情景的需要，我们将较长路劲多出来的那些点忽略 ...


    TODO:
    -------------
    1. 如何考虑坐标权重
    2. 如何考虑长路径中多出来的那些点

    """
    route1 = [ (node.x, node.y, node.weight) for node in route1 ]
    route2 = [ (node.x, node.y, node.weight) for node in route2 ]

    if len(route1) > len(route2): # 确保 route1 坐标数不超过 route2
        route1, route2 = route2, route1

    total = 0
    for x1, y1, weight in route1:
        d = np.min([ get_manhattan_distance(x1, y1, x2, y2) for x2, y2, _ in route2 ])
        total += d * weight

    return 1 / ( total / len(route1) + 1 )


def estimate_enemy_effect_on_route(route, player):
    """
    衡量敌人对我方所选的进攻路线的影响程度
    ----------------------------------------
    敌人在进攻路线两侧，可能会阻碍进攻，也就是增加了相应路线进攻的回合数，
    因此敌人的影响可以量化为相应路线长度的增加量。

    将理论路线长度与敌人的影响所导致的长度增加量相加，所得的估值可以认为是
    考虑了敌人影响后的真实路线长度，可以将这个真实路线长度对所选路线进行重新
    排序，从而选出距离短，且受敌人影响最小的攻击路线


    如何估计敌人影响？
    ------------------
    收集敌人当前所在位置所能影响到（近乎可认为是能射击到）的坐标。为了确保更加接近真实的情况，
    再假设敌人当前回合能射击，模拟敌人所有可以执行的动作（包括移动和射击，考虑射击是因为有可能可以
    摧毁一些土墙），之后同法收集敌人所能影响到的坐标。将这一坐标集所对应的区域视为受到敌人影响的区域。

    随后统计当前路径与该坐标集的重叠程度（路径上的坐标出现在该坐标集内的，可视为重叠。这种路径节点的
    数量越多，重叠程度越大），并认为这一重叠程度与敌人的影响程度正相关，也就是重叠的坐标点数与
    路径长度的增长量正相关，从而实现量化估计。

    特别的，如果敌人出现在攻击路线上，会造成较大的路线长度增加，有时甚至可以视为此路不通。


    TODO:
    ---------
    这种简单的静态分析策略可能存在对某些具体情况估计不到位的问题。当我方坦克沿着这条路线走到需要和
    敌人正面交锋的位置时，有的时候可以通过闪避直接躲开，这种情况的影响可能比较小。而有的情况下是无法躲开的，
    我方坦克只能选择往回闪避，这就相当于判定了这条路为死路 5cd24632a51e681f0e912613
    （然而事实上情况还可以更加复杂，因为实际进攻的时候，有可能会采用一些特殊的策略，让这条路转化为活路，
    例如预先打掉与我距离为 2 的墙）。
    而在静态分析中，这些具体的差别可能无法区分，因此和更加真实合理的估计间可能存在着一定的差距。

    但是采用动态分析可能不是一件很现实的事情，因为需要不断地模拟移动和模拟决策，一方面会造成算法过于
    耗时，一方面也有可能会引入各种混乱（实现无差异地在多回合模拟移动和模拟决策间回滚，并且确保面向真实情况
    决策的代码也能适用于模拟决策的情况，这将会是一个浩大的工程）。


    Input:
        - route    Route         待评估的路线
        - player   Tank2Player   将会采用这条路线的玩家对象


    """
    map_ = player._map  # 通过玩家对象引入 map 全局对象

    LENGTH_INCREMENT_OF_ENEMY_INFLUENCED = 1   # 受到敌人射击影响所导致的路线长度增量
    LENGTH_INCREMENT_OF_ENEMY_BLOCKING   = 10  # 敌人位于路线上所导致的路线长度增量

    enemyInfluencedPoints = set()  # 受敌人影响的坐标集
    enemyBlockingPoints   = set()  # 敌人阻塞的坐标集

    for oppBattler in [ oppPlayer.battler for oppPlayer in player.opponents ]:
        if oppBattler.destroyed:
            continue
        with map_.simulate_one_action(oppBattler, Action.STAY): # 刷新射击回合
            for action in oppBattler.get_all_valid_actions(): # 包含了原地停止
                with map_.simulate_one_action(oppBattler, action):
                    with map_.simulate_one_action(oppBattler, Action.STAY): # 同理刷新冷却

                        enemyBlockingPoints.add( oppBattler.xy ) # blocking
                        enemyInfluencedPoints.add( oppBattler.xy ) # 先加入敌人当前坐标

                        for dx, dy in get_searching_directions(*oppBattler.xy):
                            x, y = oppBattler.xy
                            while True:
                                x += dx
                                y += dy
                                if not map_.in_map(x, y):
                                    break
                                fields = map_[x, y]
                                if len(fields) == 0:
                                    pass
                                elif len(fields) > 1: # 两个以上敌人，不划入影响范围，并直接结束
                                    break
                                else:
                                    field = fields[0]
                                    if isinstance(field, EmptyField):
                                        pass
                                    elif isinstance(field, WaterField):
                                        continue # 水路可以认为不影响
                                    #elif isinstance(field, (BaseField, BrickField, SteelField, TankField) ):
                                    else:
                                        break #　block 类型，不划入影响范围，并直接结束

                                enemyInfluencedPoints.add( (x, y) ) # 以 pass 结尾的分支最后到达这里


    realLength = route.length # 初始为路线长度

    for node in route:
        xy = node.xy
        if xy in enemyInfluencedPoints:
            if node.weight > 0: # 射击的过渡点 weight == 0 它，它实际上不受敌人射击的影响
                realLength += LENGTH_INCREMENT_OF_ENEMY_INFLUENCED
        if xy in enemyBlockingPoints:
            # 敌人阻塞，可以影响射击点，因此同等对待
            realLength += LENGTH_INCREMENT_OF_ENEMY_BLOCKING

    return realLength


def estimate_route_blocking(route):
    """
    评估路线上 block 类型块的数量
    ----------------------------
    被用于撤退路线的评估

    撤退行为发生在己方基地，不宜过度攻击墙，否则可能会削弱基地的防御性


    实现方法
    -------------
    让 block 类型的块的权重增加，这样就可以让 block 更多的路线的长度增加


    TODO:
        是否对含有相同 block 的路线上的 block 进行进一步的评估？也就是认为基地外围的 block 的权重更高？

    """
    x2, y2 = route.end

    LENGTH_INCREMENT_OF_BLOCK           = 1  # 遇到墙，权重加 1
    LENGTH_INCREMENT_OF_INNERMOST_BLOCK = 2  # 遇到最内层的墙，权重加 2

    realLength = route.length

    for node in route:
        x1, y1 = node.xy
        if node.weight == 2: # 权重为 2 的块一定是 block 类型
            if np.abs(x1 - x2) <= 1 and np.abs(y1 - y2) <= 1: # 位于 end 的外围
                realLength += LENGTH_INCREMENT_OF_INNERMOST_BLOCK
            else:
                realLength += LENGTH_INCREMENT_OF_BLOCK

    return realLength

#{ END 'strategy/evaluate.py' }#



#{ BEGIN 'decision/abstract.py' }#

class DecisionMaker(object):
    """
    决策者的抽象基类
    ----------------

    泛指一切具有决策能力的对象，可以是具象的，例如 Team, Player
    也可以是抽象的，例如决策类

    该类的派生类对特定的决策代码段进行封装

    如果派生类是决策类，那么将实现对决策逻辑的拆分，以此来提高决策树的清晰度，提高决策逻辑的复用性

    """
    UNHANDLED_RESULT = None

    def __init__(self, *args, **kwargs):
        if self.__class__ is __class__:
            raise NotImplementedError

    def is_handled(self, result):
        """
        用于判断决策对象返回的结果是否标志着该决策适用于当前情况，用于被外部判断

        规定当该决策对象不能 handle 时，返回 __class__.UNHANDLED_RESULT
        那么只需要判断实际返回值是否与之相等，即可判断该情况是否被 handle

        """
        return result != self.__class__.UNHANDLED_RESULT

    def _make_decision(self):
        """
        真正用于被派生类重载的抽象决策接口

        如果该情况不适用，那么不需要写任何返回值，函数默认返回 None
        make_decision 函数将以此来判断该情况是否被 handle

        """
        raise NotImplementedError

    def make_decision(self):
        """
        外部可调用的决策接口
        ----------------------
        会对 _make_decision 的结果进行一些统一的处理，也可以用于在决策前后进行一些预处理和后处理操作

        此处提供一个默认的情况的处理方法：
        ----------------------------------
        - 如果真正的决策函数返回了一个 action ，则将其作为最终结果直接返回
        - 如果当前情况不适用，真正的决策函数返回了 None ，则返回 UNHANDLED_RESULT

        """
        res = self._make_decision()
        if res is None:
            return self.__class__.UNHANDLED_RESULT
        return res


class SingleDecisionMaker(DecisionMaker):
    """
    单人决策者的抽象基类，用于 Tank2Player 的个人决策

    """
    UNHANDLED_RESULT = Action.INVALID

    def __init__(self, player, signal):
        """
        重写的构造函数，确保与 Tank2Player._make_decision 接口的参数列表一致

        Input:
            - player   Tank2Player   单人玩家实例
            - signal   int           团队信号

        """
        self._player = player
        self._signal = signal

        if self.__class__ is __class__:
            raise NotImplementedError


class RespondTeamSignalDecisionMaker(SingleDecisionMaker):
    """
    用于处理团队信号的决策模型

    注意：
    ------------

    """
    UNHANDLED_RESULT = ( Action.INVALID, Signal.INVALID )
    HANDLED_SIGNALS  = (  ) # 将会处理到的团队信号

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.__class__ is __class__:
            raise NotImplementedError

    def make_decision(self):
        """
        通常来说，如果团队发送了一个信号，必须及时返回一个结果
        只有在 signal is None 的情况下，才返回 UNHANDLED_RESULT

        """
        res = self._make_decision()
        if res is None:
            signal = self._signal
            if signal in self.__class__.HANDLED_SIGNALS: # 团队信号必须得到响应
                raise Exception("team signal %d must be responded" % signal)
            return self.__class__.UNHANDLED_RESULT
        return res


class TeamDecisionMaker(DecisionMaker):
    """
    团队决策的抽象基类，用于 Tank2Team 的双人决策

    TeamDecision 与 SingleDecision 不一样，它不存在最优的决策者，
    而是所有决策者都会尝试进行一次决策。决策存在高低优先级，高优先级的决策者
    如果对某个 player 的行为进行了协调，那么低优先级的决策者不应该覆盖高优先级
    决策者的现有决策结果（当然极其特殊的决策者例外）。

    如果使用 DecisionChain 进行多个团队决策者的连续决策，
    那么整个决策链上的所有决策者必定都会进行一次决策。

    """
    def __init__(self, team):
        self._team = team  # Tank2Team

        if self.__class__ is __class__:
            raise NotImplementedError

    def is_handled(self, result):
        """
        为了适应 DecisionChain 的决策，这里重写 is_handled 函数
        使得无论如何都可以让 DecisionChain 继续
        """
        return False

    def _make_decision(self, *args, **kwargs):
        """
        派生类重写的 _make_decision 要求返回值必须是 [int, int]

        """
        raise NotImplementedError
        return [ Action.INVALID, Action.INVALID ]

    def make_decision(self):
        """
        重写 makd_decision 接口

        确保在决策完成后 player1, player2 的决策结果与返回结果同步
        这主要考虑到在决策的时候可能会忘记 create_snapshot ...

        """
        team = self._team
        player1, player2 = team.players

        action1, action2 = self._make_decision()
        player1.set_current_decision(action1)
        player2.set_current_decision(action2)

        return [ action1, action2 ]

#{ END 'decision/abstract.py' }#



#{ BEGIN 'decision/chain.py' }#

class DecisionChain(DecisionMaker):
    """
    决策链
    -------------

    效仿责任链模式，对多个决策实例进行组合，按优先级顺序依次进行决策
    如果遇到一个符合条件的决策，则将其决策结果返回，否则继续尝试低优先级的决策

    """
    UNHANDLED_RESULT = None

    def __init__(self, *decisions):
        self._decisions = decisions
        for decision in self._decisions: # 确保所有的 decision 实例均为 DecisionMaker 的派生
            assert isinstance(decision, DecisionMaker)

    def _make_decision(self):
        for decision in self._decisions:
            res = decision.make_decision()
            if decision.is_handled(res):
                return res

#{ END 'decision/chain.py' }#



#{ BEGIN 'decision/single/leave_teammate.py' }#

class LeaveTeammateDecision(RespondTeamSignalDecisionMaker):
    """
    处理两人重叠的情况
    --------------------

    1. 尝试采用安全的移动行为离开队友
    2. 避免和队友采用相同的移动方向
    3. 尽量往不导致进攻路线增加的方向移动

    """
    HANDLED_SIGNALS = ( Signal.SHOULD_LEAVE_TEAMMATE, )

    def _make_decision(self):

        player   = self._player
        signal   = self._signal
        map_     = player._map
        battler  = player.battler
        teammate = player.teammate


        if signal == Signal.SHOULD_LEAVE_TEAMMATE:

            actions = []
            for action in battler.get_all_valid_move_actions():
                if not Action.is_move(player.try_make_decision(action)): # 存在风险
                    continue
                if action == teammate.get_current_decision(): # 不能与队友的移动方向相同！
                    continue
                actions.append(action)

            if len(actions) == 0: # 没有合理的离开行为 ...
                return ( Action.STAY, Signal.CANHANDLED )

            route1 = battler.get_shortest_attacking_route()
            deltaLengths = {} #  action -> deltaLength
            for action in actions:
                with map_.simulate_one_action(battler, action):
                    route2 = battler.get_shortest_attacking_route() # 必定有路？
                    deltaLengths[action] = route2.length - route1.length # 移动后进攻路线短变短者值小

            action = min( deltaLengths.items(), key=lambda kv: kv[1] )[0]
            player.set_status(Status.READY_TO_LEAVE_TEAMMATE)
            return ( action, Signal.READY_TO_LEAVE_TEAMMATE )

#{ END 'decision/single/leave_teammate.py' }#



#{ BEGIN 'decision/single/attack_base.py' }#

class AttackBaseDecision(SingleDecisionMaker):
    """
    特殊情况决策，当下一步就要拆掉敌方基地时

    """
    def _make_decision(self):

        player  = self._player
        battler = player.battler

        # TODO:
        #   可能需要考虑一种特殊情况： 队友被杀，自己下一步打掉对方基地，但是对方下一步把我干掉
        #   这种情况下，即使我方拆掉对方基地也算平局。也许可以考虑先闪避一回合，然后再继续拆家。
        #

        if battler.is_face_to_enemy_base() and battler.canShoot:
            player.set_status(Status.READY_TO_ATTACK_BASE) # 特殊状态
            return battler.get_next_attacking_action() # 必定是射击 ...

#{ END 'decision/single/attack_base.py' }#



#{ BEGIN 'decision/single/encount_enemy.py' }#

class EncountEnemyDecision(SingleDecisionMaker):
    """
    遭遇敌人时的决策

    """
    def _make_decision(self):

        player   = self._player
        signal   = self._signal
        map_     = player._map
        tank     = player.tank
        battler  = player.battler
        teammate = player.teammate

        Tank2Player = type(player)
        BattleTank  = type(battler)

        aroundEnemies = battler.get_enemies_around()
        if len(aroundEnemies) > 0:
            player.set_status(Status.ENCOUNT_ENEMY)

            if len(aroundEnemies) > 1: # 两个敌人，尝试逃跑
                assert len(aroundEnemies) == 2 # 可能会遇到极其罕见的三人重叠

                # 首先判断是否为真正的双人夹击
                enemy1, enemy2 = aroundEnemies
                x, y = tank.xy
                x1, y1 = enemy1.xy
                x2, y2 = enemy2.xy

                # 先判断敌人是否重叠，如果是，那么很有可能直接击杀！
                if (x1, y1) == (x2, y2):
                    if (not teammate.defeated # 队友还没有死，自己可以考虑牺牲
                        and battler.canShoot
                        ):
                        player.set_status(Status.ENCOUNT_TWO_ENEMY)
                        player.set_status(Status.READY_TO_DOUBLE_KILL_ENEMIES)
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        return battler.shoot_to(enemy1)

                if x1 == x2 == x:
                    if (y > y1 and y > y2) or (y < y1 and y < y2):
                        player.set_status(Status.ENCOUNT_ONE_ENEMY)
                        pass # 实际可视为一个人
                elif y1 == y2 == y:
                    if (x > x1 and x > x2) or (x < x1 and x < x2):
                        player.set_status(Status.ENCOUNT_ONE_ENEMY)
                        pass
                else: # 真正的被夹击
                    player.set_status(Status.ENCOUNT_TWO_ENEMY)
                    oppBattlers = [ BattleTank(_enemy) for _enemy  in aroundEnemies ]
                    if all( oppBattler.canShoot for oppBattler in oppBattlers ):
                        # 如果两者都有弹药，可能要凉了 ...
                        player.set_status(Status.DYING)
                        if battler.canShoot:
                            # TODO: 这种情况下有选择吗？
                            player.set_status(Status.READY_TO_FIGHT_BACK)
                            return battler.shoot_to(enemy1) # 随便打一个？
                    elif all( not oppBattler.canShoot for oppBattler in oppBattlers ):
                        # 均不能进攻的话，优先闪避到下回合没有敌人的位置（优先考虑拆家方向）
                        firstMoveAction = tuple()
                        attackAction = battler.get_next_attacking_action()
                        if Action.is_move(attackAction): # 如果是移动行为
                            firstMoveAction = ( attackAction, )
                        for action in firstMoveAction + Action.MOVE_ACTIONS:
                            if map_.is_valid_move_action(tank, action):
                                with map_.simulate_one_action(tank, action):
                                    if len( battler.get_enemies_around() ) < 2: # 一个可行的闪避方向
                                        player.set_status(Status.READY_TO_DODGE)
                                        return action
                        # 均不能闪避，应该是处在狭道内，则尝试任意攻击一个
                        if battler.canShoot:
                            # TODO: 是否有选择？
                            player.set_status(Status.READY_TO_FIGHT_BACK)
                            return battler.shoot_to(enemy1) # 随便打一个
                    else: # 有一个能射击，则反击他
                        for oppBattler in oppBattlers:
                            if oppBattler.canShoot: # 找到能射击的敌人
                                actions = battler.try_dodge(oppBattler)
                                if len(actions) == 0: # 不能闪避
                                    if battler.canShoot:
                                        player.set_status(Status.READY_TO_FIGHT_BACK)
                                        return battler.shoot_to(oppBattler)
                                    else: # 要凉了 ...
                                        break
                                elif len(actions) == 1:
                                    action = player.try_make_decision(actions[0])
                                else:
                                    action = player.try_make_decision(actions[0],
                                                player.try_make_decision(actions[1]))
                                if Action.is_move(action): # 统一判断
                                    player.set_status(Status.READY_TO_DODGE)
                                    return action
                                # 没有办法？尝试反击
                                if battler.canShoot:
                                    player.set_status(Status.READY_TO_FIGHT_BACK)
                                    return battler.shoot_to(oppBattler)
                                else: # 要凉了
                                    break
                        # 没有办法对付 ..
                        player.set_status(Status.DYING)
                    # 无所谓的办法了...
                    return player.try_make_decision(battler.get_next_attacking_action())

            # TODO:
            #   虽然说遇到了两个一条线上的敌人，但是这不意味着后一个敌人就没有威胁 5ccee460a51e681f0e8e5b17


            # 当前情况：
            # ---------
            # 1. 敌人数量为 2 但是一个处在另一个身后，或者重叠，可视为一架
            # 2. 敌人数量为 1
            #
            if len(aroundEnemies) == 1:
                oppTank = aroundEnemies[0]
            else: # len(aroundEnemies) == 2:
                oppTank = battler.get_nearest_enemy()
            oppBattler = BattleTank(oppTank)
            oppPlayer = Tank2Player(oppBattler)

            #
            # (inserted) 判断上回合敌人是否和我重叠，用于标记敌人 5ce52a48d2337e01c7a714c7
            #
            if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                and not player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=2)
                and not Action.is_move(player.get_previous_action(back=1)) # 且不是因为我方主动打破重叠导致
                ): # 上回合刚刚进入重叠，这回合就被打破
                with map_.rollback_to_previous():
                    if oppTank is battler.get_overlapping_enemy():
                        oppPlayer.add_labels(Label.IMMEDIATELY_BREAK_OVERLAP_BY_MOVE)


            #
            # 在非 WITHDRAW 的情况下，评估当前侵略性
            #
            if not player.has_status(Status.WITHDRAW):
                _allowWithdraw = ( WithdrawalDecision.ALLOW_WITHDRAWAL
                                    and not player.has_label(Label.DONT_WITHDRAW) )
                status = evaluate_aggressive(battler, oppBattler, allow_withdraw=_allowWithdraw)
                player.set_status(status)
            else:
                status = Status.WITHDRAW

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
                            player.set_status(Status.READY_TO_KILL_ENEMY)
                            return battler.shoot_to(oppBattler)

                    attackAction = battler.get_next_attacking_action() # 其他情况，优先进攻，不与其纠缠
                    realAction = player.try_make_decision(attackAction) # 默认的进攻路线
                    if Action.is_stay(realAction): # 存在风险
                        if Action.is_move(attackAction):
                            #
                            # 原本移动或射击，因为安全风险而变成停留，这种情况可以尝试射击，充分利用回合数
                            #
                            # TODO:
                            #   实际上，很多时候最佳路线选择从中线进攻，但从两侧进攻也是等距离的，
                            #   在这种情况下，由于采用从中线的进攻路线，基地两侧的块并不落在线路上，因此会被
                            #   忽略，本回合会被浪费。但是进攻基地两侧的块往往可以减短路线。因此此处值得进行
                            #   特殊判断
                            #
                            fields = battler.get_destroyed_fields_if_shoot(attackAction)
                            route = battler.get_shortest_attacking_route()
                            for field in fields:
                                if route.has_block(field): # 为 block 对象，该回合可以射击
                                    action = player.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        player.set_status(Status.PREVENT_BEING_KILLED)
                                        player.set_status(Status.KEEP_ON_MARCHING)
                                        return action
                            # TODO: 此时开始判断是否为基地外墙，如果是，则射击
                            for field in fields:
                                if battler.check_is_outer_wall_of_enemy_base(field):
                                    action = player.try_make_decision(battler.shoot_to(field))
                                    if Action.is_shoot(action):
                                        player.set_status(Status.PREVENT_BEING_KILLED)
                                        player.set_status(Status.KEEP_ON_MARCHING)
                                        return action


                        # 刚刚对射为两回合，该回合双方都没有炮弹，尝试打破僵局
                        #---------------------------------------------------
                        # 当前为侵略性的，并且在对方地盘，尝试回退一步，与对方重叠。
                        #   后退操作必须要有限制 5cd10315a51e681f0e900fa8
                        #
                        # 如果一直回头，尝试在这一步选择非回头的其他行为 5ced8eee641dd10fdcc7907f
                        #
                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=3)
                            and Action.is_stay(player.get_previous_action(back=2))    # 还需要检查两者上上回合是否为等待
                            and Action.is_stay(oppPlayer.get_previous_action(back=2)) # 避免将边移动边对射的情况考虑进来
                            and battler.is_in_enemy_site()         # 添加必须在对方地盘的限制，避免在我方地盘放人
                            and player.has_status(Status.AGGRESSIVE) # 只有侵略性的状态可以打破僵局
                            ):
                            # 判断是否为反复回头
                            if player.has_status_recently(Status.READY_TO_BACK_AWAY, turns=6): # 最近几回合内是否曾经回头过
                                player.add_labels(Label.ALWAYS_BACK_AWAY)

                            if (player.has_label(Label.ALWAYS_BACK_AWAY)
                                and not battler.is_in_our_site(include_midline=True) # 严格不在我方基地
                                ): # 考虑用闪避的方式代替后退
                                for action in battler.try_dodge(oppBattler):
                                    realAction = player.try_make_decision(action)
                                    if Action.is_move(realAction):
                                        player.set_status(Status.TRY_TO_BREAK_ALWAYS_BACK_AWAY)
                                        player.remove_labels(Label.ALWAYS_BACK_AWAY) # 删掉这个状态
                                        return realAction

                            # 否则继续回头
                            backMoveAction = battler.back_away_from(oppBattler)
                            action = player.try_make_decision(backMoveAction)
                            if Action.is_move(action):
                                player.set_status(Status.READY_TO_BACK_AWAY)
                                return action


                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=1) # 上回合正在和对方对射
                            and not battler.canShoot    # 但是我方本回合不能射击
                            and not oppBattler.canShoot # 并且对方本回合不能射击
                            ):
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射状态，用于后方打破僵持

                        # 其余情况照常
                        player.set_status(Status.PREVENT_BEING_KILLED)
                        return realAction
                    # 否则不予理会，直接移动或者反击
                    action = player.try_make_decision(battler.get_next_attacking_action())
                    if not Action.is_stay(action):
                        # 补丁
                        #----------------------------
                        # 针对两者距离为 2 的情况，不能一概而论！
                        #
                        if status == Status.STALEMENT: # 僵持模式考虑堵路
                            _route = battler.get_route_to_enemy_by_move(oppBattler)
                            if _route.is_not_found():
                                _route = battler.get_route_to_enemy_by_move(oppBattler, block_teammate=False)
                            assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                            assert _route.length > 0, "unexpected overlapping enemy"
                            if _route.length == 2:
                                if not player.is_suitable_to_overlap_with_enemy(oppBattler): # 更适合堵路
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                        # 其他情况均可以正常移动
                        #player.set_status(Status.KEEP_ON_MARCHING)
                        #return action
                        return # 直接抛出让后面的 decision 处理，当做没有这个敌人

                    #  不能移动，只好反击
                    action = player.try_make_decision(battler.shoot_to(oppBattler))
                    if Action.is_shoot(action):
                        player.set_status(Status.READY_TO_FIGHT_BACK)
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
                        #
                        # 首先把堵路的思路先做了，如果不能射击，那么同 aggressive
                        #
                        # TODO:
                        #   有的时候这并不是堵路，而是在拖时间！ 5ccf84eca51e681f0e8ede59

                        # 上一回合保持重叠，但是却被敌人先过了，这种时候不宜僵持，应该直接走人
                        # 这种情况下直接转为侵略模式！
                        #
                        if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                            and (player.has_status_in_previous_turns(Status.READY_TO_BLOCK_ROAD, turns=1)
                                or player.has_status_in_previous_turns(Status.KEEP_ON_OVERLAPPING, turns=1))
                            ):
                            pass # 直接过到侵略模式
                        else:
                            # 否则算作正常的防守
                            #
                            # TODO:
                            #   射击不一定正确，因为敌人可能上回合刚把我过掉，此时应该考虑主动闪走！
                            #   5ce4e66cd2337e01c7a6abd7
                            #
                            if battler.canShoot:

                                #
                                # (inserted) 先看上回合是不是刚被对方过掉
                                #
                                _justBreakOverlap = False
                                with map_.rollback_to_previous():
                                    if (battler.has_overlapping_enemy()
                                        and oppTank is battler.get_overlapping_enemy()
                                        ): # 刚刚被对手打破重叠
                                        _justBreakOverlap = True

                                _shouldShoot = False
                                if _justBreakOverlap: # 刚刚被对手主动打破重叠
                                    for _route in battler.get_all_shortest_attacking_routes():
                                        if oppTank.xy in _route:  # 对方现在位于我的攻击路线上，说明对方上回合是
                                            _shouldShoot = True   # 回头堵路，那么继续保持射击
                                            break

                                if _shouldShoot: # 正常防御
                                    player.set_status(Status.READY_TO_BLOCK_ROAD, Status.READY_TO_FIGHT_BACK)
                                    if battler.on_the_same_line_with(oppBattler, ignore_brick=False):
                                        player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射
                                    return battler.shoot_to(oppBattler)
                                else:
                                    pass # 否则视为进攻逻辑

                    # 闪避，尝试找最佳方案
                    #-------------------------
                    defenseAction = Action.STAY
                    if battler.canShoot:
                        defenseAction = battler.shoot_to(oppBattler)


                    dodgeActions = battler.try_dodge(oppTank)

                    if battler.is_in_enemy_site(): # 限制条件，只有在对方基地才开始闪现！

                        #
                        # 最佳方向是闪避向着进攻方向移动
                        #
                        attackAction = battler.get_next_attacking_action()
                        for action in dodgeActions: # 与进攻方向相同的方向是最好的
                            if Action.is_same_direction(action, attackAction):
                                realAction = player.try_make_decision(action) # 风险评估
                                if Action.is_move(realAction):
                                    player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                    return realAction # 闪避加行军


                        # 没有最佳的闪避方案，仍然尝试闪避
                        #-----------------------------
                        # 但是不能向着增加攻击线路长短的方向闪避！
                        #
                        route1 = battler.get_shortest_attacking_route()
                        for action in dodgeActions:
                            realAction = player.try_make_decision(action)
                            if Action.is_move(realAction):
                                with map_.simulate_one_action(battler, action):
                                    route2 = battler.get_shortest_attacking_route()
                                if route2.length > route1.length: # 不能超过当前路线长度，否则就是浪费一回合
                                    continue
                                else:
                                    player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                    return realAction

                        #
                        # 此时还可以考虑借力
                        # 假设下回合两方对射，如果我方尝试闪避，对方会恰好打掉我方进攻路线上的块，那么就闪避
                        #
                        if (len(dodgeActions) > 0         # 存在可用的闪避行为
                            and battler.is_in_enemy_site() # 限制为只有在对方基地才适用这个逻辑
                            ):
                            _shouldDodge = False
                            action = dodgeActions[0]
                            enemyShootAction = oppBattler.shoot_to(battler)
                            with outer_label() as OUTER_BREAK:
                                with map_.simulate_one_action(battler, action): # 假设闪走
                                    fields = oppBattler.get_destroyed_fields_if_shoot(enemyShootAction)
                                    for field in fields:
                                        if isinstance(field, BrickField): # 对手会打掉墙
                                            for _route in battler.get_all_shortest_attacking_routes():
                                                if field.xy in _route: # 这个块在某一个最短的攻击路线上
                                                    _shouldDodge = True
                                                    raise OUTER_BREAK
                            if _shouldDodge:
                                for action in dodgeActions:
                                    realAction = player.try_make_decision(action)
                                    if Action.is_move(realAction):
                                        player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                        return realAction

                    #
                    # 没有不能不导致路线变长的办法，如果有炮弹，那么优先射击！
                    # 5ccef443a51e681f0e8e64d8
                    #-----------------------------------
                    route1 = battler.get_shortest_attacking_route()
                    if Action.is_shoot(defenseAction):
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        if battler.on_the_same_line_with(oppBattler, ignore_brick=False):

                            # (inserted) 刚刚对射为两回合，该回合尝试闪避敌人，打破僵局
                            #--------------------------------------------
                            # 尝试往远处闪避，创造机会
                            #
                            # 此外，由于敌人这回合必定射击，那么他的炮弹可能会打掉我身后的墙
                            # 这样的可能会创造一些新的机会。有的时候导致该回合必须要与敌人对射的原因，可能是因为
                            # 没有办法开辟攻击路线，而不是敌人堵路。由于闪避的方向是不允许的，也就是另一个更近的
                            # 闪避反向上必定是一个无法摧毁也不能移动到的块，否则会被与先摧毁。
                            # 此时如果可以往背离敌人的方向移动，那么应该不会陷入对射僵局。但事实上是进入了
                            # 这就说明别离敌人的方向是无法移动到的。如果它恰好是一块土墙，那么就可以靠这回合和敌人接力
                            # 来摧毁掉，也许还有往下移动的可能。 5ce429fad2337e01c7a5cd61
                            #
                            if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=4)
                                and Action.is_stay(player.get_previous_action(back=1)) # 检查对应的两个冷却回合是停止
                                and Action.is_stay(player.get_previous_action(back=3)) # 避免将移动对射的情况被考虑进来
                                and Action.is_stay(oppPlayer.get_previous_action(back=1))
                                and Action.is_stay(oppPlayer.get_previous_action(back=3))
                                and battler.is_in_enemy_site()           # 添加必须在对方地盘的限制，避免在我方地盘放人
                                and player.has_status(Status.AGGRESSIVE) # 只有侵略性的状态可以打破僵局
                                ):
                                for action in battler.try_dodge(oppBattler):
                                    if Action.is_move(action):
                                        realAction = player.try_make_decision(action)
                                        if Action.is_move(realAction):
                                            player.set_status(Status.READY_TO_DODGE)
                                            # 这里还是再判断一下距离
                                            route1 = battler.get_shortest_attacking_route()
                                            with map_.simulate_one_action(battler, action):
                                                route2 = battler.get_shortest_attacking_route()
                                                if route2.length > route1.length:
                                                    player.set_status(Status.WILL_DODGE_TO_LONG_WAY)
                                            return realAction

                            # 默认是优先射击
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY)
                            return defenseAction


                    # 如果不能射击，那么终究还是要闪避的
                    # 或者是无法后方移动，为了打破僵局，尝试闪避
                    #----------------------------------
                    for action in dodgeActions:
                        realAction = player.try_make_decision(action)
                        if Action.is_move(realAction):
                            player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                            #
                            # 因为这种情况很有可能会出现死循环 5cd009e0a51e681f0e8f3ffb
                            # 为了后续能够打破这种情况，这里额外添加一个状态进行标记
                            #
                            player.set_status(Status.WILL_DODGE_TO_LONG_WAY)
                            return realAction

                    if Action.is_stay(defenseAction):
                        #
                        # 其实还有一种情况，那就是危险的敌人在自己身上！ 5ceaaacdd2337e01c7adf6a4
                        #
                        riskyEnemyBattler = player.get_risky_enemy()
                        if (riskyEnemyBattler is not None
                            and riskyEnemyBattler is not oppBattler
                            and riskyEnemyBattler.xy == battler.xy
                            ): # 这种情况下实际是没有威胁的 ...
                            for action in dodgeActions:
                                player.set_status(Status.KEEP_ON_MARCHING, Status.READY_TO_DODGE)
                                # TODO:
                                #   还需要判断是否向远路闪避 ...
                                #   这里的细节还需要优化，或者这个和自己重叠的条件在前面就要穿插进去
                                return action

                        player.set_status(Status.DYING) # 否则就凉了 ...

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
                # attackAction = self.try_make_decision(battler.get_next_attacking_action()) # 默认的侵略行为
            elif status == Status.DEFENSIVE:
                if not oppBattler.canShoot:

                    if len( oppBattler.try_dodge(battler) ) == 0:
                        if battler.canShoot: # 必死情况
                            player.set_status(Status.READY_TO_KILL_ENEMY)
                            return battler.shoot_to(oppBattler)
                    #
                    # 不能马上打死，敌人又无法攻击
                    #-------------------------------
                    # 优先堵路，根据双方距离判断
                    #
                    _route = battler.get_route_to_enemy_by_move(oppBattler)
                    if _route.is_not_found():
                        _route = battler.get_route_to_enemy_by_move(oppBattler, block_teammate=False)
                    assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                    assert _route.length > 0, "unexpected overlapping enemy"

                    if _route.length == 1: # 双方相邻，选择等待

                        # 此处首先延续一下对射状态
                        if (player.has_status_in_previous_turns(Status.OPPOSITE_SHOOTING_WITH_ENEMY, turns=1) # 上回合正在和对方对射
                            and not battler.canShoot    # 但是我方本回合不能射击
                            and not oppBattler.canShoot # 并且对方本回合不能射击
                            ):
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 保持对射状态，用于后方打破僵持

                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY
                    elif _route.length > 2: # 和对方相隔两个格子以上
                        if player.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全逼近
                            action = battler.move_to(oppBattler)
                            player.set_status(Status.READY_TO_BLOCK_ROAD) # 可以认为在堵路 ...
                            return action
                        else:
                            player.set_status(Status.READY_TO_BLOCK_ROAD)
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
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                                map_.revert()
                                # 否则直接冲上去
                                if player.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全移动
                                    moveAction = battler.move_to(oppBattler)
                                    player.set_status(Status.READY_TO_BLOCK_ROAD) # 可以认为在堵路
                                    return moveAction
                                else: # 冲上去不安全，那就只能等到了
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return Action.STAY
                        else:
                            # 对手当前回合可以闪避，那么尝试冲上去和他重叠
                            # TODO:
                            #   可能弄巧成拙 5cca97a4a51e681f0e8ad227
                            #
                            #   这个问题需要再根据情况具体判断！
                            #
                            '''
                            if player.is_safe_to_close_to_this_enemy(oppBattler): # 可以安全重叠
                                moveAction = battler.move_to(oppBattler)
                                player.set_status(Status.READY_TO_BLOCK_ROAD)
                                return moveAction
                            else: # 有风险，考虑等待
                                player.set_status(Status.READY_TO_BLOCK_ROAD)
                                return Action.STAY
                            '''
                            #
                            # TODO:
                            #   是否应该根据战场情况进行判断，比如停下来堵路对方一定无法走通？
                            #
                            #   假设自己为钢墙然后搜索对方路径？
                            #
                            player.set_status(Status.READY_TO_BLOCK_ROAD)
                            return Action.STAY"""
                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY # 似乎没有比这个这个更好的策略 ...
                # 对方可以射击
                else:
                    if battler.canShoot: # 优先反击
                        player.set_status(Status.READY_TO_FIGHT_BACK)
                        if battler.on_the_same_line_with(oppBattler, ignore_brick=False):
                            player.set_status(Status.OPPOSITE_SHOOTING_WITH_ENEMY) # 触发对射状态
                        return battler.shoot_to(oppBattler)
                    # 不能反击，只好闪避
                    actions = battler.try_dodge(oppBattler)
                    if len(actions) == 0:
                        player.set_status(Status.DYING) # 凉了 ...
                        action = Action.STAY
                    elif len(actions) == 1:
                        action = player.try_make_decision(actions[0])
                    else: # len(actions) == 2:
                        action = player.try_make_decision(actions[0],
                                        player.try_make_decision(actions[1]))
                    if Action.is_move(action): # 统一判断
                        player.set_status(Status.READY_TO_DODGE)
                        return action
                    # 否则就凉了 ...
                    player.set_status(Status.DYING)

                return Action.STAY

            #
            # 回撤模式
            #------------
            # 1. 优先回撤
            # 2. 如果处在守卫状况，根据所处位置，选择反击或堵路
            #
            elif status == Status.WITHDRAW:
                base = map_.bases[battler.side]
                if not battler.is_closest_to(base):
                    with player.create_snapshot():
                        decision = WithdrawalDecision(player, signal)
                        action = decision.make_decision()
                        if decision.is_handled(action):
                            with map_.simulate_one_action(battler, action):
                                if oppTank not in battler.get_enemies_around(): # 安全行为
                                    return  # 留给 withdraw 处理
                else:
                    # 现在我方坦克已经处在基地附近
                    with player.create_snapshot():
                        decision = BaseDefenseDecision(player, signal)
                        action = decision.make_decision()
                        if decision.is_handled(action): # 符合 base defense 的条件
                            with map_.simulate_one_action(battler, action):
                                if oppTank not in battler.get_enemies_around(): # 安全行为
                                    return  # 留给 base defense
                #
                # 否则就是不安全行为，应该予以反击
                #
                if battler.canShoot:
                    player.set_status(Status.READY_TO_FIGHT_BACK)
                    return battler.shoot_to(oppBattler)
                elif oppBattler.canShoot: # 否则应该闪避
                    for action in battler.try_dodge(oppBattler):
                        player.set_status(Status.READY_TO_DODGE)
                        return action

                if oppBattler.canShoot:
                    player.set_status(Status.DYING) # 不然就凉了 ...

                # 最后就等待
                return Action.STAY

#{ END 'decision/single/encount_enemy.py' }#



#{ BEGIN 'decision/single/overlapping.py' }#

class OverlappingDecision(SingleDecisionMaker):
    """
    与敌人重合时的决策
    ------------------------

    侵略模式
    --------
    1. 直奔对方基地，有机会就甩掉敌人

    防御模式
    --------
    1. 尝试回退堵路
    2. 对于有标记的敌人，考虑采用其他的策略，例如尝试击杀敌军


    多回合僵持后，会有主动打破重叠的决策

    """
    def _make_decision(self):

        player  = self._player
        signal  = self._signal
        map_    = player._map
        tank    = player.tank
        battler = player.battler

        Tank2Player = type(player)
        BattleTank  = type(battler)

        if battler.has_overlapping_enemy():

            player.set_status(Status.ENCOUNT_ENEMY)
            player.set_status(Status.OVERLAP_WITH_ENEMY)
            oppTank = battler.get_overlapping_enemy()
            oppBattler = BattleTank(oppTank)
            oppPlayer = Tank2Player(oppBattler)

            if not player.has_status(Status.WITHDRAW):
                _allowWithdraw = ( WithdrawalDecision.ALLOW_WITHDRAWAL
                                    and not player.has_label(Label.DONT_WITHDRAW) )
                status = evaluate_aggressive(battler, oppBattler, allow_withdraw=_allowWithdraw)
                player.set_status(status)
            else:
                status = Status.DEFENSIVE  # 看作是防御

            #
            # 先检查对方上回合是否在跟随我移动，以及时切换决策模式 ...
            #   5cd3f56d86d50d05a0083621 / 5ccec5a6a51e681f0e8e46c2 / 5ce26520d2337e01c7a3ca2b
            #-------------------------------
            if (player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                and Action.is_move(player.get_previous_action(back=1))
                ):
                oppPlayer.add_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY)

            if (oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY)
                and player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=3)
                and all( Action.is_stay(player.get_previous_action(_back)) for _back in range(1, 3+1) )
                ): # 如果和一个带有跟随重叠标记的敌人僵持超过 3 回合，就把这个标记移除，因为它此时已经不是一个会和我马上打破重叠的敌人了
                oppPlayer.remove_labels(Label.BREAK_OVERLAP_SIMULTANEOUSLY) # 5ce3c990d2337e01c7a54b4c

            if (oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY)
                and Action.is_shoot(player.get_previous_action(back=1))
                and Action.is_shoot(oppPlayer.get_previous_action(back=1))
                # TODO: 是否有必要判断射击方向相同？
                ): # 如果和一个带有跟随重叠标记的敌人在同一回合采用射击的方式打破重叠，则对这个行为进一步标记
                oppPlayer.add_labels(Label.SIMULTANEOUSLY_SHOOT_TO_BREAK_OVERLAP)

            #
            # (inserted) 如果敌人带有立即打破重叠的标记，那么如果还能执行到这个地方，就意味着敌人
            # 上次打破重叠的方向是回防（如果是进攻，那么应该不会再有机会遭遇）
            #
            # 那么在此处重新进入重叠的时候，尝试将对手击杀
            #
            if not status == Status.DEFENSIVE: # 防御模式不触发？
                if (oppPlayer.has_label(Label.IMMEDIATELY_BREAK_OVERLAP_BY_MOVE)
                    and not player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY) # 上回合不重叠
                    ):
                    action = battler.get_next_attacking_action()
                    if Action.is_move(action):
                        if battler.canShoot:
                            player.set_status(Status.READY_TO_BREAK_OVERLAP,
                                              Status.ATTEMPT_TO_KILL_ENEMY)
                            return action + 4

            #
            # (inserted) 观察到大多数人在遇到重叠时会选择直接无视对手，我们也可以学习一下这种决策
            # 但是目前不想让这个决策成为必须，希望它只在特定的状况下被触发。
            #
            # 对于非防御模式下，考虑这样三种情况：
            # -------------------------------------
            # 1. 假设我方当前进攻路线距离领先一步 ，如果对方主动打破重叠，这时，如果对方下一步可以闪避，
            #    而我方当前回合不饿能闪避，必须要还击（之所以必须要射击是因为我们考虑最坏的情况，假设
            #    对方这回合会还击，如果我方这时候不还击就会被打掉），假如对方这回合闪避了，并且恰好沿着进攻
            #    方向闪避，那么结束后对方将比我方领先一步，这时候即使再继续攻击，结局也很可能是输，
            #    因此这步可以考虑主动打破重叠
            #
            # 2. 假设我方当前进攻路线长度与敌方相同，假设对方主动打破重叠，假设对方可以闪避并且可以向着
            #    进攻方向闪避，那么对方很有可能比我方快一步，此时应该主动打破重叠。假如对方不能向着进攻方向
            #    闪避，那么认为敌人一定会还击，此时考虑我方下回合是否可以向着进攻方向闪避，如果不可以的话，
            #    我方就和对方差一步，处于劣势，那么就主动打破重叠。
            #
            # 3. 假设对方比我方领先一步，这种情况下多属于对方处在我方阵营，我方很可能会触发防御模式
            #    这种情况下就直接忽略掉吧
            #
            route1 = battler.get_shortest_attacking_route()
            route2 = oppBattler.get_shortest_attacking_route()
            _shouldActiveBreakOverlap = False
            _enemyAttackAction = Action.STAY
            if route1.is_not_found() or route2.is_not_found(): # 虽然应该不可能，但是还是判断一下
                pass
            else:
                _leadingLength = route2.length - route1.length # 我方领先步数
                debug_print(battler, _leadingLength)
                action = battler.get_next_attacking_action(route1)
                if Action.is_shoot(action):
                    # TODO:
                    #   是否有必要考虑射击行为？
                    pass

                elif _leadingLength == 1: # 情况一

                    allRoutes = oppBattler.get_all_shortest_attacking_routes()
                    #
                    # 由于不同的路线下一步可能会走到相同的地方，而造成的结果相同
                    # 因此此处将相同的行为进行缓存，为了减少判断次数
                    _consideredActions = set()
                    for route in allRoutes:
                        _enemyAttackAction = oppBattler.get_next_attacking_action(route)
                        if _enemyAttackAction in _consideredActions:
                            continue
                        _consideredActions.add(_enemyAttackAction)

                        if not Action.is_move(_enemyAttackAction):
                            # 只考虑移动行为，因为，假如对方当前回合射击，那么我方下回合可以移动
                            # 这时双方距离可以认为相等，很有可能平局
                            continue

                        # 提交地图模拟这步行为，这个时候双方应该均为僵持
                        with map_.simulate_one_action(oppBattler, _enemyAttackAction):

                            # 考虑下回合我方是否可以闪避
                            with player.create_snapshot():

                                # 确保这种情况下决策不会再运行到这里，因为此时将不再和敌人重叠，于是不会遇到递归无终点
                                action, _ = player.make_decision(signal=signal)
                                if action != battler.shoot_to(oppBattler):
                                    # 说明下回合我方可以闪避，那么就可以不管了
                                    continue

                            # 我方下回合不可以闪避，考虑敌人下回合是否可以闪避
                            with oppPlayer.create_snapshot():
                                action, _ = oppPlayer.make_decision()
                                if action != oppBattler.shoot_to(battler):
                                    # 说明下回合敌人可以闪避
                                    _shouldActiveBreakOverlap = True
                                    break

                elif _leadingLength == 0: # 情况二

                    allRoutes = oppBattler.get_all_shortest_attacking_routes()
                    _consideredActions = set()
                    for route in allRoutes:

                        _enemyAttackAction = oppBattler.get_next_attacking_action(route)
                        if _enemyAttackAction in _consideredActions:
                            continue
                        _consideredActions.add(_enemyAttackAction)

                        if not Action.is_move(_enemyAttackAction):
                            # TODO:
                            #   仍然不考虑射击？为了防止无迭代终点？
                            continue

                        # 提交一步模拟，敌方应该比我方领先一步
                        with map_.simulate_one_action(oppBattler, _enemyAttackAction):

                            # 考虑下回合敌方是否可以闪避
                            with oppPlayer.create_snapshot():
                                action, _ = oppPlayer.make_decision()
                                if action != oppBattler.shoot_to(battler): # 敌方可以闪避
                                    _shouldActiveBreakOverlap = True
                                    break

                            # 对方下回合不可以闪避，那么考虑我方是否可以闪避
                            with player.create_snapshot():
                                action, _ = player.make_decision()
                                # TODO:
                                #   我方下回合可能是防御状态，这种情况下必定反击，判断不准确
                                #
                                #   不过问题其实不大，因为这样就会触发主动打破重叠
                                #
                                if action == battler.shoot_to(oppBattler): # 我方不能闪避
                                    _shouldActiveBreakOverlap = True
                                    break
                else:
                    # 其他情况，留作下一回合打破重叠
                    pass

            if _shouldActiveBreakOverlap:
                action = battler.get_next_attacking_action(route1)
                if Action.is_move(action):
                    if player.is_safe_to_break_overlap_by_move(action, oppBattler):
                        player.set_status(Status.READY_TO_BREAK_OVERLAP)
                        player.set_status(Status.KEEP_ON_MARCHING)
                        return action
                elif Action.is_shoot(action):
                    #
                    # 假设下一步射击，考虑最糟糕的一种情况，那就是敌人同一回合主动打破重叠，移动到我方身后
                    # 而我方无法闪避，那么就有被敌人击杀的风险
                    #
                    _mayBeKilled = False
                    with map_.simulate_one_action(oppBattler, _enemyAttackAction):
                        with map_.simulate_one_action(battler, action):
                            if len(battler.try_dodge(oppBattler)) == 0: # 无法闪避！
                                _mayBeKilled = True

                    if not _mayBeKilled: # 在没有被击杀风险的情况下可以采用射击
                        return action


            # 是否已经有多回合僵持，应该主动打破重叠
            _shouldBreakOverlap = (
                battler.canShoot # 可以射击
                and player.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                ) # 上回合重叠这回合还重叠，就视为僵持，趁早打破重叠

            if status == Status.AGGRESSIVE:
                # 对方不能射击，对自己没有风险，或者是符合了主动打破重叠的条件
                if not oppBattler.canShoot or _shouldBreakOverlap:
                    # 尝试继续行军
                    action = battler.get_next_attacking_action()
                    if Action.is_move(action):
                        if _shouldBreakOverlap:
                            #
                            # 首先先处理主动打破重叠的情况的情况
                            # 该情况下会改用定制的安全性测试函数判断情况
                            #
                            # TODO:
                            #   优先尝试不往上回合已经移动过的方向移动 5ce26520d2337e01c7a3ca2b
                            #
                            realAction = action

                            #
                            # 如果遇到和我打破重叠时机一致的对手
                            #-------------------
                            # 1. 尝试换一个方向移动
                            # 2. 如果不能换方向，那么可能在狭道内，那么退回原来的位置，
                            #    这意味着如果敌人下回合开炮，那么他必死 5ce264c2d2337e01c7a3c9f6
                            #
                            if oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY):
                                #
                                # 禁止的行为不一定是反向！因为可能恰好遇到拐弯 ...
                                # 5ce48707d2337e01c7a641b7 / 5ce487a6d2337e01c7a64205
                                #
                                _backTurn = 0
                                previousAction = Action.STAY
                                while Action.is_stay(previousAction): # 有可能上回合是等待，也就是
                                    _backTurn += 1  # 上回合又下方决策得到，因此需要一直回查到移动行为
                                    previousAction = player.get_previous_action(back=_backTurn)

                                forbiddenAction = action
                                revertMoveAction = (previousAction + 2) % 4  # 反向移动的行为
                                #
                                # 尝试移向其他的方向
                                #
                                # TODO:
                                #   太难判断了，还是暂时先禁止把 ... 鬼知道对面怎么算的距离
                                #
                                '''if realAction == forbiddenAction:
                                    route1 = battler.get_shortest_attacking_route()
                                    for optionalAction in battler.get_all_valid_move_actions():
                                        if (optionalAction == forbiddenAction
                                            or optionalAction == revertMoveAction # 不要回头
                                            ):
                                            continue
                                        with map_.simulate_one_action(battler, optionalAction):
                                            route2 = battler.get_shortest_attacking_route()
                                            if route2.length <= route1.length: # 移动后不增加攻击距离s
                                                realAction = optionalAction
                                                break'''

                                #
                                # 尝试反向移动
                                #
                                # TODO:
                                #   事实上反向移动也不一定是正确的，因为每一个人对于这种情况的判断是不一样的
                                #   5ce4943ed2337e01c7a64cdd
                                #
                                '''if realAction == forbiddenAction:
                                    with map_.simulate_one_action(battler, revertMoveAction):
                                        if len(oppBattler.try_dodge(battler)) == 0: # 如果这回合他反向射击，那么必死
                                            realAction = revertMoveAction'''

                                #
                                # 否则等待，让敌人开一炮，这样下回合还会继续触发移动
                                # 有可能换一个敌方就可以有别的决策方法
                                # 也有可能直接带到基地 5ce48b77d2337e01c7a644e5
                                #
                                if realAction == forbiddenAction:
                                    player.set_status(Status.OVERLAP_WITH_ENEMY) # 保持等待状况
                                    return Action.STAY


                            if player.is_safe_to_break_overlap_by_move(realAction, oppBattler):
                                player.set_status(Status.READY_TO_BREAK_OVERLAP)
                                player.set_status(Status.KEEP_ON_MARCHING)
                                return realAction
                            else:
                                # 无法安全移动，但是又需要打破重叠，那么就视为防御
                                # 让后续的代码进行处理
                                player.remove_status(Status.AGGRESSIVE)
                                player.set_status(Status.DEFENSIVE)
                                pass # 这里会漏到 DEFENSIVE
                        else:
                            # 开始处理常规情况
                            realAction = player.try_make_decision(action)
                            if Action.is_move(realAction): # 继续起那就
                                player.set_status(Status.KEEP_ON_MARCHING)
                                return realAction
                            # 否则就是等待了，打得更有侵略性一点，可以尝试向同方向开炮！
                            realAction = player.try_make_decision(action + 4)
                            if Action.is_shoot(realAction):
                                player.set_status(Status.KEEP_ON_MARCHING)
                                return realAction

                    elif Action.is_shoot(action): # 下一步预计射击
                        realAction = player.try_make_decision(action)
                        if Action.is_shoot(realAction):
                            player.set_status(Status.KEEP_ON_MARCHING)
                            return realAction
                    else: # 否则停留
                        player.set_status(Status.KEEP_ON_OVERLAPPING)
                        return Action.STAY
                else:
                    player.set_status(Status.KEEP_ON_OVERLAPPING)
                    return Action.STAY # 原地等待


            if status == Status.DEFENSIVE or _shouldBreakOverlap:

                # 对方不能射击，对自己没有风险，或者是符合了主动打破重叠的条件
                if not oppBattler.canShoot or _shouldBreakOverlap:
                    #
                    # 这里不只思考默认的最优路径，而是将所有可能的最优路径都列举出来
                    # 因为默认的最优路径有可能是破墙，在这种情况下我方坦克就不会打破重叠
                    # 这就有可能错失防御机会
                    #
                    for enemyAttackRoute in oppBattler.get_all_shortest_attacking_routes():
                        oppAction = oppBattler.get_next_attacking_action(enemyAttackRoute) # 模拟对方的侵略性算法
                        if Action.is_move(oppAction) or Action.is_shoot(oppAction): # 大概率是移动
                            # 主要是为了确定方向
                            oppAction %= 4

                            # 首先先检查对方是否会跟随我
                            #--------------------------
                            # 1. 如果我方可以射击，对方不能射击，那么按照之前的经验，对方下回合会移动
                            #    这个时候尝试击杀
                            #
                            if oppPlayer.has_label(Label.BREAK_OVERLAP_SIMULTANEOUSLY):
                                if battler.canShoot: # 这回合可以射击，则改为射击
                                    if (oppPlayer.has_label(Label.SIMULTANEOUSLY_SHOOT_TO_BREAK_OVERLAP)
                                        and oppBattler.canShoot # 如果带有这个标记，那么这回合就不要射击了，等待敌人打完这回合，
                                        ): # 下回合才有可能击杀 5ce50cd9d2337e01c7a6e45a
                                        player.set_status(Status.KEEP_ON_OVERLAPPING)
                                        return Action.STAY
                                    else: # 否则就考虑反身射击
                                        player.set_status(Status.READY_TO_BREAK_OVERLAP,
                                                          Status.ATTEMPT_TO_KILL_ENEMY) # 尝试击杀敌军
                                        return oppAction + 4
                                else:
                                    pass # 均不能射击，那么将判定为没有风险。那就一起移动

                            # 正常情况下选择堵路
                            #----------------------
                            if player.is_safe_to_break_overlap_by_move(oppAction, oppBattler): # 模仿敌人的移动方向
                                player.set_status(Status.READY_TO_BREAK_OVERLAP)
                                player.set_status(Status.READY_TO_BLOCK_ROAD) # 认为在堵路
                                return oppAction

                # 否则等待
                player.set_status(Status.READY_TO_BLOCK_ROAD)
                player.set_status(Status.KEEP_ON_OVERLAPPING)
                return Action.STAY

#{ END 'decision/single/overlapping.py' }#



#{ BEGIN 'decision/single/base_defense.py' }#

class BaseDefenseDecision(SingleDecisionMaker):
    """
    主动防守基地
    ---------------------
    现在没有和敌人正面相遇，首先先处理一种特殊情况

    在敌人就要攻击我方基地的情况下，应该优先移动，而非预判击杀
    这种防御性可能会带有自杀性质


    若敌人当前回合正面对我方基地
    ----------------------------
    1. 敌人当前回合炮弹冷却，下回合射向我方基地，如果我方坦克下一步可以拦截，那么优先移动拦截
    2. 敌人当前回合可以射击，我方坦克下一步可以拦截，那么自杀性拦截
    3. 敌人当前回合炮弹冷却，下回合射向我方基地，而我方坦克需要两步才能拦截，那么自杀性拦截


    若敌人下一回合可以面对我方基地
    ----------------------------
    1. 此时敌人必定可以射击，如果我方坦克在这一步可以优先移动到拦截的位置，那么优先移动

    """
    def _make_decision(self):

        player  = self._player
        map_    = player._map
        battler = player.battler


        for oppBattler in [ _oppPlayer.battler for _oppPlayer in player.opponents ]:
            if oppBattler.destroyed:
                continue

            #
            # 敌人当前回合面向基地
            #
            if oppBattler.is_face_to_enemy_base():
                if oppBattler.canShoot: # 敌方可以射击
                    for action in battler.get_all_valid_move_actions():
                        with map_.simulate_one_action(battler, action):
                            if not oppBattler.is_face_to_enemy_base(): # 此时不再面向我方基地，为正确路线
                                player.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                return action
                else: # 敌方不可射击
                    for action in battler.get_all_valid_move_actions(): # 敌方不能射击，我方尝试移动两步
                        with map_.simulate_one_action(battler, action):
                            if not oppBattler.is_face_to_enemy_base(): # 一步防御成功
                                player.set_status(Status.BLOCK_ROAD_FOR_OUR_BASE)
                                return action
                            else: # 尝试两步拦截
                                if map_.is_valid_move_action(battler, action): # 需要先预判是否合理
                                    with map_.simulate_one_action(battler, action):
                                        if not oppBattler.is_face_to_enemy_base(): # 两步拦截成功
                                            player.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                            return action
            else:
                #
                # 敌人下一回合可能面向基地
                #
                for enemyAction in oppBattler.get_all_valid_move_actions():
                    with map_.simulate_one_action(oppBattler, enemyAction):
                        if oppBattler.is_face_to_enemy_base(): # 敌人移动一步后面向我方基地
                            for action in battler.get_all_valid_move_actions():
                                with map_.simulate_one_action(battler, action):
                                    if not oppBattler.is_face_to_enemy_base(): # 我方优先移动可以阻止
                                        player.set_status(Status.BLOCK_ROAD_FOR_OUR_BASE)
                                        return action

#{ END 'decision/single/base_defense.py' }#



#{ BEGIN 'decision/single/behind_brick.py' }#

class BehindBrickDecision(RespondTeamSignalDecisionMaker):
    """
    适用于在墙后和敌人僵持时的情况

    """
    HANDLED_SIGNALS = ( Signal.PREPARE_FOR_BREAK_BRICK,
                        Signal.READY_TO_BACK_AWAY_FROM_BRICK, )

    def _make_decision(self):

        player  = self._player
        signal  = self._signal
        battler = player.battler


        BattleTank = type(battler)

        # 准备破墙信号
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

            attackAction = battler.get_next_attacking_action() # 只考虑攻击路径上的敌人
            oppTank = battler.get_enemy_behind_brick(attackAction, interval=-1)

            '''_undoRevertTurns = 0
            while oppTank is None: #　对应于敌方刚离开的那种触发条件
                # 可能存在多轮回滚，因为别人的策略和我们的不一样！
                # 给别人回滚的时候必须要考虑多回合！
                map_.revert()
                _undoRevertTurns += 1
                oppTank = battler.get_enemy_behind_brick(attackAction, interval=-1)'''

            if oppTank is None:
                #
                # 墙后敌人并不一定处于攻击路径之后! 5ce3d1c0d2337e01c7a554e3
                # 在这种情况下应该取消考虑这种情况
                #
                res = ( Action.INVALID, Signal.UNHANDLED )

            else:

                player.set_status(Status.WAIT_FOR_MARCHING)      # 用于下回合触发
                player.set_status(Status.HAS_ENEMY_BEHIND_BRICK) # 用于下回合触发
                player.set_risky_enemy(oppTank) # 重新设置这个敌人！

                dodgeActions = battler.try_dodge(oppTank)
                if len(dodgeActions) == 0:
                    # 准备凿墙
                    breakBrickActions = battler.break_brick_for_dodge(oppTank)
                    if len(breakBrickActions) == 0: # 两边均不是土墙
                        res = ( Action.STAY, Signal.CANHANDLED ) # 不能处理，只好等待
                    else:
                        player.set_status(Status.READY_TO_PREPARE_FOR_BREAK_BRICK)
                        res = ( breakBrickActions[0], Signal.READY_TO_PREPARE_FOR_BREAK_BRICK )
                else:
                    # 可以闪避，那么回复团队一条消息，下一步是破墙动作
                    shootAction = battler.shoot_to(oppTank)
                    player.set_status(Status.READY_TO_BREAK_BRICK)
                    res = ( shootAction, Signal.READY_TO_BREAK_BRICK )

                '''for _ in range(_undoRevertTurns):
                    map_.undo_revert()'''

            return res  # 必定回复一个信号

        #
        # 准备回退以制造二打一的局面
        #
        if signal == Signal.SUGGEST_TO_BACK_AWAY_FROM_BRICK:

            attackAction = battler.get_next_attacking_action() # 只考虑攻击路径上的敌人
            oppTank = battler.get_enemy_behind_brick(attackAction, interval=-1)

            if oppTank is None: # ??
                res = ( Action.INVALID, Signal.UNHANDLED )
            else:

                player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)

                action = battler.back_away_from(oppTank)
                realAction = player.try_make_decision(action)

                if Action.is_move(realAction):
                    player.set_status(Status.READY_TO_BACK_AWAY_FROM_BRICK)
                    res = ( realAction, Signal.READY_TO_BACK_AWAY_FROM_BRICK )

                else: # 存在风险，也就是想要夹击的敌人有炮弹，那么就先等待一回合
                    res = ( Action.STAY, Signal.CANHANDLED )

            return res  # 必定回复一个信号

#{ END 'decision/single/behind_brick.py' }#



#{ BEGIN 'decision/single/follow_enemy_behind_brick.py' }#

class FollowEnemyBehindBrickDecision(SingleDecisionMaker):
    """
    跟随墙后敌人的逻辑
    -----------------
    如果上回合敌人和我方隔墙僵持，然后敌人向两侧移动，为了防止敌人从旁边的墙突破，
    这里添加一个主动跟随的逻辑，假如对方这回合破墙，那么我方这回合就会出现在对方墙后，
    这样对方就无法进攻，甚至可以为我方进攻创造机会 5ce57677d2337e01c7a7c1ff

    """
    def _make_decision(self):

        player  = self._player
        map_    = player._map
        battler = player.battler

        Tank2Player = type(player)
        BattleTank  = type(battler)

        if (player.has_status_in_previous_turns(Status.HAS_ENEMY_BEHIND_BRICK, turns=1)
            and not Action.is_move(player.get_previous_action(back=1))
            ): # 上回合墙后有人
            with map_.rollback_to_previous():
                action = battler.get_next_attacking_action()
                if Action.is_stay(action):
                    return
                oppTank = battler.get_enemy_behind_brick(action, interval=-1) # 找到墙后敌人
                if oppTank is None:  # 理论上不会存在？
                    return

                oppBattler = BattleTank(oppTank)
                oppPlayer  = Tank2Player(oppBattler)

                dodgeActions = oppBattler.try_dodge(battler)


            previousAction = oppPlayer.get_previous_action(back=1)
            if Action.is_stay(previousAction):
                return

            if previousAction in dodgeActions: # 敌人上回合从墙后闪开
                realAction = player.try_make_decision(previousAction) # 尝试跟随敌人上回合的移动行为
                if Action.is_move(realAction):
                    with map_.simulate_one_action(battler, realAction):
                        for field in battler.get_destroyed_fields_if_shoot(action):
                            if isinstance(field, BrickField):
                                # 确保跟随后还隔着墙 5ce90a90d2337e01c7abcd07
                                # 否则何必要跟随 ...
                                player.set_status(Status.READY_TO_FOLLOW_ENEMY)
                                return realAction


        #
        # 将动作连续化，如果对方连续移动，那么可以考虑跟随
        #
        if player.has_status_in_previous_turns(Status.READY_TO_FOLLOW_ENEMY):
            oppTank = None
            with map_.auto_undo_revert() as counter: # 有可能要多回合回滚
                while map_.revert():
                    counter.increase()
                    action = battler.get_next_attacking_action()
                    if Action.is_stay(action):
                        continue
                    oppTank = battler.get_enemy_behind_brick(action, interval=-1)
                    if oppTank is not None:
                        oppBattler = BattleTank(oppTank)
                        oppPlayer = Tank2Player(oppBattler)
                        break

            if oppTank is not None: # 理论上一定会找到敌人
                previousAction = oppPlayer.get_previous_action(back=1)
                lastAction = player.get_previous_action(back=1) # 上回合一定跟随移动
                # 确保敌人在贴着墙移动，否则就不必继续跟随了
                if np.abs(previousAction % 4 - lastAction % 4) in (0, 2): # 两次移动方向或相反
                    realAction = player.try_make_decision(previousAction) # 尝试跟随敌人上回合行为
                    if Action.is_move(realAction):
                        with map_.simulate_one_action(battler, realAction):
                            for field in battler.get_destroyed_fields_if_shoot(action):
                                if isinstance(field, BrickField):
                                    player.set_status(Status.READY_TO_FOLLOW_ENEMY)
                                    return realAction

#{ END 'decision/single/follow_enemy_behind_brick.py' }#



#{ BEGIN 'decision/single/withdrawal.py' }#

class WithdrawalDecision(SingleDecisionMaker):
    """
    主动回撤逻辑
    -------------
    如果我方大逆风，那么主动回防基地

    具有一个持久性的记忆标签 KEEP_ON_WITHDRAWING

    带有这个标签的 player 在决策的时候，比 WithdrawalDecision 优先级高的决策应该以
    WITHDRAW 状态为优先

    带有 WITHDRAW 持久标记的 player 决策必定会在此处终止，否则就要取消这个标记和状态，
    让后续的决策继续进行

    """
    ALLOW_WITHDRAWAL = True  # 一个测试用的 const，设为 False 则取消一切和 WITHDRAW 相关的决策


    @CachedProperty
    def _GUARD_POINTS(self):
        """
        获得基地两个对角线位置的两个防御坐标

        """
        player = self._player
        map_ = player._map
        tank = player.tank
        side = tank.side
        base = map_.bases[side]

        _DIAGONAL_DIRECTIONS = ( (1, 1), (1, -1), (-1, 1), (-1, -1) )

        x1, y1 = base.xy
        points = []
        for dx, dy in _DIAGONAL_DIRECTIONS:
            x2 = x1 + dx
            y2 = y1 + dy
            if map_.in_map(x2, y2):
                points.append( (x2, y2) )

        return points


    def _get_more_dangerous_guard_point(self, oppBattler):
        """
        更加危险的防御点，被认为是距离敌人更近的防御点
        """
        player  = self._player
        battler = player.battler
        _GUARD_POINTS = self._GUARD_POINTS

        distancesToEnemy = [ oppBattler.get_manhattan_distance_to_point(x2, y2)
                                for (x2, y2) in _GUARD_POINTS ]
        return _GUARD_POINTS[ np.argmin(distancesToEnemy) ] # 距离敌人更近的点根据危险性


    def _is_dangerous_action(self, action, oppBattler):
        """
        为了防止出现这样一种情况： 5ce9154fd2337e01c7abd81f
        以及这样一种情况： 5cea5d38d2337e01c7ad8418
        ----------------------------------

        1. 假如我方这回合移动，而敌人下回合通过非射击行为，可以面向我方基地（射击行为的话，下回合对方炮弹冷却，
           对基地暂时不造成威胁），如果我方这回合选择不移动可以阻止它，那么就选择停止

        2. 假如我方这回合射击，而敌人下回合通过非射击行为，可以面向我方基地，那么就选择停止

        3. 假如我方先破一墙，对方出现在后面，那么就算是有威胁

        """
        player  = self._player
        battler = player.battler
        map_    = battler._map

        if (Action.is_move(action)
            and not oppBattler.is_face_to_enemy_base() # 事实上应该不会出现
            ):
            # 先保存所有可能行为，为了防止模拟我方行为后，射击能力被重置
            _shouldStay = False
            enemyAction = Action.STAY
            with map_.simulate_one_action(battler, action):
                for _action in oppBattler.get_all_valid_move_actions() + [ Action.STAY ]:
                    with map_.simulate_one_action(oppBattler, _action):
                        if oppBattler.is_face_to_enemy_base():
                            # 我方执行一步后，对方面对基地
                            _shouldStay = True
                            enemyAction = _action
                            break
            if _shouldStay:
                # 现在不模拟我方行为，然后同样模拟对方行为，看对方是否面对我方基地
                with map_.simulate_one_action(oppBattler, enemyAction):
                    if not oppBattler.is_face_to_enemy_base():
                        return True


        if (Action.is_shoot(action)
            and not oppBattler.is_face_to_enemy_base() # 敌人上回合没有面对我方基地
            ):
            for _action in oppBattler.get_all_valid_move_actions() + [ Action.STAY ]:
                with map_.simulate_one_action(oppBattler, _action):
                    if not oppBattler.is_face_to_enemy_base(): # 当敌人尚未面对我方基地
                        with map_.simulate_one_action(battler, action):
                            if oppBattler.is_face_to_enemy_base(): # 我方射击一步后，敌人面对我方基地
                                return True  # 不安全的

        # 其他情况均认为安全
        return False


    def _try_make_decision(self, action, oppBattler):
        """
        Withdraw 下的 try_make_decision

        """
        player = self._player
        Tank2Player = type(player)
        oppPlayer = Tank2Player(oppBattler)
        realAction = player.try_make_decision(action)

        if (Action.is_stay(realAction)
            and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=2)
            and player.has_status_in_previous_turns(Status.WAIT_FOR_WITHDRAWING, turns=2)
            and not Action.is_shoot(oppPlayer.get_previous_action(back=1))
            and not Action.is_shoot(oppPlayer.get_previous_action(back=2))
            ): # 如果等待了两回合，对方两回合均为射击那么视为安全
            player.set_status(Status.FORCED_WITHDRAW) # 糟糕的设计！如果后续需要更改，那么需要在再删掉这个状态
            realAction = action

        if (Action.is_stay(realAction)
            and not player.has_status(Status.FORCED_WITHDRAW)
            ):
            return Action.STAY

        if self._is_dangerous_action(realAction, oppBattler):
            player.remove_status(Status.FORCED_WITHDRAW)
            return Action.STAY

        return realAction


    def _get_next_action_to_guard_point(self, x2, y2, oppBattler):
        """
        获得趋近守卫点 (x2, y2) 的下一个行为
        """
        player  = self._player
        battler = player.battler
        map_    = player._map
        base    = map_.bases[battler.side]

        route = battler.get_route_to_point_by_move(x2, y2)
        assert not route.is_not_found() # 这个必定能找到路！

        action = battler.get_next_defensive_action(route)
        realAction = self._try_make_decision(action, oppBattler)

        if not Action.is_stay(realAction):
            with map_.simulate_one_action(battler, realAction):
                if not battler.is_closest_to(base):
                    player.remove_status(Status.FORCED_WITHDRAW)
                    return Action.STAY  # 其实是可以确保一直停留在基地附近的？

        return realAction # stay/realAction


    def _make_decision(self):

        if not self.__class__.ALLOW_WITHDRAWAL:
            return self.__class__.UNHANDLED_RESULT

        player  = self._player
        signal  = self._signal
        map_    = player._map
        battler = player.battler
        base    = map_.bases[battler.side]
        x2, y2  = base.xy

        Tank2Player = type(player)
        BattleTank  = type(battler)

        oppTank = battler.get_nearest_enemy()
        oppBattler = BattleTank(oppTank)
        oppPlayer = Tank2Player(oppBattler)

        status = evaluate_aggressive(battler, oppBattler, allow_withdraw=self.__class__.ALLOW_WITHDRAWAL)

        #
        # 首先，检查带有持久化 WITHDRAW 标签的 player
        # 该回合是否还需要真正的延续这个标签
        #
        # 一种情况是考虑是否应该
        #
        if (player.has_label(Label.KEEP_ON_WITHDRAWING)
            and status != Status.WITHDRAW  # 实际评估不是 WITHDRAW
            ):
            strictStatus = evaluate_aggressive(battler, oppBattler, strict=True)
            if strictStatus == Status.AGGRESSIVE: # 假如对方上回合被击杀，那么我方大概率会触发侵略模式？
                player.remove_status(Status.WITHDRAW)
                player.remove_labels(Label.KEEP_ON_WITHDRAWING)
                player.set_status(status)
                return # 留给其他 decision 处理
        #
        # 一种情况是考虑上回合是否击杀了一个人
        #
        if len([ _oppPlayer for _oppPlayer in player.opponents if _oppPlayer.defeated ]) == 1:
            teammate = player.teammate
            if not teammate.defeated: # 二打一的局势，此时 oppBattler 为剩下一个敌人
                teammateBattler = teammate.battler
                _dontWithdraw = False
                _deltaDistanceToEnemy = battler.get_manhattan_distance_to(oppBattler) - teammateBattler.get_manhattan_distance_to(oppBattler)
                if _deltaDistanceToEnemy > 0: # 我比队友距离更远
                    _dontWithdraw = True
                elif _deltaDistanceToEnemy == 0: # 一样远
                    _deltaDistanceToOurBase = battler.get_manhattan_distance_to(base) - teammateBattler.get_manhattan_distance_to(base)
                    if _deltaDistanceToOurBase > 0: # 我比队友理基地更远，那么让队友防御
                        _dontWithdraw = True
                    elif _deltaDistanceToOurBase == 0: # 如果还是一样远 ...
                        if not teammate.has_label(Label.DONT_WITHDRAW): # 避免两者同时强攻，那么就让先判断的队友进行强攻
                            _dontWithdraw = True

                if _dontWithdraw:
                    player.remove_status(Status.WITHDRAW)
                    player.remove_labels(Label.KEEP_ON_WITHDRAWING)
                    player.add_labels(Label.DONT_WITHDRAW)
                    return # 留给其他 decision 处理


        if status == Status.WITHDRAW or player.has_status(Status.WITHDRAW):

            player.remove_labels(Status.AGGRESSIVE, Status.DEFENSIVE, Status.STALEMENT)
            player.set_status(Status.WITHDRAW)
            player.add_labels(Label.KEEP_ON_WITHDRAWING) # 这个状态一旦出现，就添加标记

            #
            # (inserted) 不要轻易从中线撤退，应该想一下是否可以堵路
            #
            if battler.is_near_midline(offset=2): # y = [2, 6]
                for action in [ Action.STAY ] + battler.get_all_valid_move_actions(): # 先判断 stay
                    with map_.simulate_one_action(battler, action):
                        if battler.can_block_this_enemy(oppBattler):
                            player.set_status(Status.READY_TO_BLOCK_ROAD)
                            return action  # 不需要判断安全性？

            #
            # 1. 如果上回合已经到达基地附近，那么优先移动到基地对角线的位置等待
            # 2. 必要时改变守卫的位置
            #
            # TODO:
            #   如果能直接到达守卫点，那应该考虑一下直接到达 ... 而不要先把基地的墙凿了
            #
            if battler.is_closest_to(base):
                player.set_status(Status.GRARD_OUR_BASE)

                moreDangerousPoint = None
                _shouldMoveToDangerousPoint = False
                #
                # 已到达基地附近，但是未到达守卫点，尝试移向守卫点
                #
                if (battler.xy not in self._GUARD_POINTS  # 为处在对角线防御位置
                    and not player.has_status(Status.BLOCK_ROAD_FOR_OUR_BASE) # 高优先级触发
                    ):
                    moreDangerousPoint = self._get_more_dangerous_guard_point(oppBattler)
                    _shouldMoveToDangerousPoint = True


                #
                # 已经到达守卫点，判断是否需要移向另一个守卫点
                #
                if battler.xy in self._GUARD_POINTS:
                    distancesToEnemy = [ oppBattler.get_manhattan_distance_to_point(x2, y2)
                                            for (x2, y2) in self._GUARD_POINTS ]
                    moreDangerousPoint = self._GUARD_POINTS[ np.argmin(distancesToEnemy) ] # 距离敌人更近的点根据危险性
                    _shouldMoveToDangerousPoint = True

                if _shouldMoveToDangerousPoint:
                    action = self._get_next_action_to_guard_point(*moreDangerousPoint, oppBattler)
                    if not Action.is_stay(action):
                        player.set_status(Status.MOVE_TO_ANOTHER_GUARD_POINT)
                    else:
                        player.set_status(Status.STAY_FOR_GUARDING_OUR_BASE)
                    return action

                player.set_status(Status.STAY_FOR_GUARDING_OUR_BASE) # 设置为等待
                return Action.STAY # 其他情况下继续等待

            _route1 = battler.get_shortest_defensive_route()
            _route2 = oppBattler.get_shortest_attacking_route()        # 如果不将我视为钢墙
            _route3 = oppBattler.get_shortest_attacking_route(
                            ignore_enemies=False, bypass_enemies=True) # 如果将我视为钢墙

            # TODO:
            #   如果 route2 和 route3 距离差很大，那么可以选择不动
            #
            if _route2.is_not_found() or _route3.is_not_found(): # 对方找不到进攻路线，那就相当于我方把路堵住了？
                return Action.STAY

            assert not _route1.is_not_found() # 这个不可能的吧

            allowedDelay = _route2.length - (_route1.length - 2) # 我方防御路线比地方进攻路线领先值
            allowedDelay -= 1  # 至少要快一步
            if allowedDelay < 0:
                allowedDelay = 0

            returnAction = Action.INVALID
            with outer_label() as OUTER_BREAK:
                for route in sorted( battler.get_all_shortest_defensive_routes(delay=allowedDelay),
                                        key=lambda route: estimate_route_blocking(route) ): # 阻塞程度最小的优先

                    action = battler.get_next_defensive_action(route)

                    if Action.is_stay(action) and battler.is_closest_to(base): # 到达基地就等待了
                        returnAction = action
                        raise OUTER_BREAK

                    realAction = self._try_make_decision(action, oppBattler)

                    if Action.is_stay(realAction): # 尽量找一条不是停留的路？
                        player.remove_status(Status.FORCED_WITHDRAW)
                        continue

                    returnAction = realAction
                    raise OUTER_BREAK

            if not Action.is_valid(returnAction): # 没有一个合适的行为？
                action = battler.get_next_defensive_action(_route1) # 那就随便来一个把 ...
                returnAction = self._try_make_decision(action, oppBattler)

            if Action.is_move(returnAction) or Action.is_shoot(returnAction):
                player.set_status(Status.READY_TO_WITHDRAW)
            else: # stay
                if battler.is_closest_to(base):
                    player.set_status(Status.STAY_FOR_GUARDING_OUR_BASE)
                else:
                    if player.get_risky_enemy() is not None: # 存在风险敌人就能判定是因为敌人阻挡？
                        player.set_status(Status.WAIT_FOR_WITHDRAWING)
                        player.set_status(Status.PREVENT_BEING_KILLED)

            return returnAction

#{ END 'decision/single/withdrawal.py' }#



#{ BEGIN 'decision/single/active_defense.py' }#

class ActiveDefenseDecision(SingleDecisionMaker):
    """
    主动防御策略
    -----------------------

    不要追击敌人，而是选择保守堵路策略！

    1. 对于路线差为 2 的情况，选择堵路，而非重叠
    2. 如果自己正常行军将会射击，那么判断射击所摧毁的块是否为敌人进攻路线上的块
       如果是，则改为移动或者停止

    """

    ACTIVE_DEFENSE_MIN_TRIGGER_TURNS = 2  # 前两回合结束前不要触发主动防御！


    def _make_decision(self):

        player  = self._player
        signal  = self._signal
        map_    = player._map
        tank    = player.tank
        battler = player.battler

        Tank2Player = type(player)
        BattleTank  = type(battler)


        oppTank = battler.get_nearest_enemy() # 从路线距离分析确定最近敌人
        oppBattler = BattleTank(oppTank)
        oppPlayer = Tank2Player(oppBattler)
        _allowWithdraw = ( WithdrawalDecision.ALLOW_WITHDRAWAL
                            and not player.has_label(Label.DONT_WITHDRAW) )
        status = evaluate_aggressive(battler, oppBattler, allow_withdraw=_allowWithdraw)
        player.set_status(status)

        if status == Status.DEFENSIVE:
            # 避免过早进入 DEFENSIVE 状态
            #----------------------------
            currentTurn = map_.turn
            if currentTurn < __class__.ACTIVE_DEFENSE_MIN_TRIGGER_TURNS and False: # 取消主动防御轮数限制？
                player.remove_status(Status.DEFENSIVE)
                player.set_status(Status.AGGRESSIVE)   # 前期以侵略性为主
            else:
                # 如果是距离为 2
                #----------------
                # 由于两者相对的情况在前面的 encount enemy 时会被处理，这里如果遇到这种情况
                # 那么说明两者是出于不相对的对角线位置。
                #
                _route = battler.get_route_to_enemy_by_move(oppBattler)
                if _route.is_not_found():
                    _route = battler.get_route_to_enemy_by_move(oppBattler, block_teammate=False)
                assert not _route.is_not_found(), "route not found ?" # 必定能找到路！
                assert _route.length > 0, "unexpected overlapping enemy"
                if _route.length == 2:
                    #
                    # 此时应该考虑自己是否正处在敌方的进攻的必经之路上
                    # 如果是这样，那么考虑不动，这样最保守
                    # 否则在合适的回合冲上去挡路
                    #
                    # 判定方法是将己方坦克分别视为空白和钢墙，看对方的最短路线长度是否有明显延长
                    # 如果有，那么就堵路
                    #
                    # 需要能够正确应对这一局的情况 5cd356e5a51e681f0e921453
                    # TODO:
                    #   事实上这一局敌方不管往左还是往右，都是8步，因此这里会判定为不堵路，所以就会主动重叠
                    #   但是，左右两边的走法是不一样的，往左走必定会走不通，左右的8步并不等价，这里需要还需要
                    #   进一步的分析路线的可走性
                    #
                    # TODO:
                    #   事实上这样不一定准确，因为如果敌人前面有一个土墙，那么他可以先打掉土墙
                    #   然后继续前移，这样敌方就可以选择继续往前移动
                    #
                    enemyAttackRoute1 = oppBattler.get_shortest_attacking_route(ignore_enemies=True, bypass_enemies=False)
                    enemyAttackRoute2 = oppBattler.get_shortest_attacking_route(ignore_enemies=False, bypass_enemies=True)
                    if enemyAttackRoute2.length > enemyAttackRoute1.length: # 路线增长，说明是必经之路
                        player.set_status(Status.ACTIVE_DEFENSIVE)
                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY

                    #
                    # 虽然路线长度相同，但是路线的可走性不一定相同，这里先衡量对方当前路线的可走性
                    # 如果本回合我方等待，敌人向前移动，那么敌方只有在能够不向原来位置闪避的情况下
                    # 才算是我堵不住他的路，否则仍然视为堵路成功 5cd356e5a51e681f0e921453
                    #
                    x0, y0 = oppBattler.xy # 保存原始坐标
                    enemyMoveAction = oppBattler.get_next_attacking_action(enemyAttackRoute1)
                    # ssert Action.is_move(enemyMoveAction) # 应该是移动
                    _shouldStay = False
                    with map_.simulate_one_action(oppBattler, enemyMoveAction):
                        if battler.get_manhattan_distance_to(oppBattler) == 1: # 此时敌方与我相邻
                            _shouldStay = True # 这种情况才是真正的设为 True 否则不属于此处应当考虑的情况
                            for enemyDodgeAction in oppBattler.try_dodge(battler):
                                with map_.simulate_one_action(oppBattler, enemyDodgeAction):
                                    if oppBattler.xy != (x0, y0): # 如果敌人移动后可以不向着原来的位置闪避
                                        _shouldStay = False # 此时相当于不能堵路
                                        break
                    if _shouldStay:
                        player.set_status(Status.ACTIVE_DEFENSIVE)
                        player.set_status(Status.READY_TO_BLOCK_ROAD)
                        return Action.STAY

                    #
                    # 否则自己不处在敌方的必经之路上，考虑主动堵路
                    #
                    if (not oppBattler.canShoot # 对方这回合不能射击
                        or (Action.is_stay(oppPlayer.get_previous_action(back=1))
                            and Action.is_stay(oppPlayer.get_previous_action(back=2))
                            ) # 或者对方等待了两个回合，视为没有危险
                        ):    # 不宜只考虑一回合，否则可能会出现这种预判错误的情况 5cdd894dd2337e01c79e9bed
                        for moveAction in battler.get_all_valid_move_actions():
                            with map_.simulate_one_action(battler, moveAction):
                                if battler.xy in enemyAttackRoute1: # 移动后我方坦克位于敌方坦克进攻路线上
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return moveAction

                        # 我方的移动后仍然不会挡敌人的路？？
                        for moveAction in battler.get_all_valid_move_actions(middle_first=True): # 中路优先
                            with map_.simulate_one_action(battler, moveAction):
                                if battler.get_manhattan_distance_to(oppBattler) == 1: # 如果移动后与敌人相邻
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return moveAction

                        # 否则，就是和敌人接近的连个方向上均为不可走的！
                        # 那么让后续的逻辑进行处理
                        pass

                    '''
                    if (
                            # 可能是主动防御但是为了防止重叠而等待
                            (
                                player.has_status_in_previous_turns(Status.ACTIVE_DEFENSIVE, turns=1)
                                and player.has_status_in_previous_turns(Status.READY_TO_BLOCK_ROAD, turns=1)
                                and Action.is_stay(player.get_previous_action(back=1))
                            )

                        or
                            # 可能是为了防止被杀而停止
                            (
                                player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED)
                                and Action.is_stay(player.get_previous_action(back=1))
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
                                with map_.simulate_one_action(oppBattler, enemyMoveAction):
                                    for enemyDodgeAction in oppBattler.try_dodge(battler): # 如果敌人上前后可以闪避我
                                        route1 = oppBattler.get_shortest_attacking_route()
                                        with map_.simulate_one_action(oppBattler, enemyDodgeAction):
                                            route2 = oppBattler.get_shortest_attacking_route()
                                            if route2.length <= route1.length: #　并且闪避的路线不是原路返回
                                                _shouldMove = True
                                                break

                            #
                            # 真正的值得堵路的情况
                            #
                            if _shouldMove:
                                x1, y1 = battler.xy
                                x2, y2 = _route[1].xy # 跳过开头
                                moveAction = Action.get_move_action(x1, y1, x2, y2)
                                if map_.is_valid_move_action(battler, moveAction): # 稍微检查一下，应该本来是不会有错的
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                                    return moveAction

                    #
                    # 否则选择不要上前和敌人重叠，而是堵路
                    #
                    player.set_status(Status.ACTIVE_DEFENSIVE)
                    player.set_status(Status.READY_TO_BLOCK_ROAD)
                    return Action.STAY'''

                # endif


                # 转向寻找和敌方进攻路线相似度更高的路线
                #--------------------------------------
                #
                enemyAttackRoute = oppBattler.get_shortest_attacking_route()
                closestAttackRoute = max( battler.get_all_shortest_attacking_routes(delay=3), # 允许 3 步延迟
                                            key=lambda r: estimate_route_similarity(r, enemyAttackRoute) ) # 相似度最大的路线

                #
                # 判断下一步是否可以出现在敌人的攻击路径之上 5cd31d84a51e681f0e91ca2c
                #-------------------------------
                # 如果可以，就移动过去
                #
                for moveAction in battler.get_all_valid_move_actions():
                    with map_.simulate_one_action(battler, moveAction):
                        x3, y3 = battler.xy # 获得移动后的坐标

                    if (x3, y3) in enemyAttackRoute:
                        _willMove = False # 是否符合移动的条件

                        realAction = player.try_make_decision(moveAction)
                        if Action.is_move(realAction):
                            _willMove = True
                        elif player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1): # 打破僵局
                            oppBattler = player.get_risky_enemy()
                            oppPlayer = Tank2Player(oppBattler)
                            if (oppBattler.canShoot # 当回合可以射击
                                and not oppPlayer.has_status_in_previous_turns(Status.RELOADING) # 上回合也可以射击
                                ): # 说明敌人大概率不打算攻击我
                                _willMove = True

                        #
                        # 符合了移动的条件
                        # 但是还需要检查移动方向
                        # 不能向着远离敌人的方向移动，不然就会后退 ... 5cd33351a51e681f0e91da39
                        #
                        if _willMove:
                            distance1 = battler.get_manhattan_distance_to(oppBattler)
                            with map_.simulate_one_action(battler, moveAction):
                                distance2 = battler.get_manhattan_distance_to(oppBattler)
                                if distance2 > distance1: # 向着远处移动了
                                    pass
                                else:
                                    # 添加一个限制，必须要移动后出现在敌人的附近
                                    # 否则约束过弱，容易导致前期乱跑的情况 5cd39434a51e681f0e924128
                                    #
                                    for enemy in oppBattler.get_enemies_around():
                                        if enemy is tank:
                                            player.set_status(Status.ACTIVE_DEFENSIVE)
                                            player.set_status(Status.READY_TO_BLOCK_ROAD)
                                            return moveAction


                attackAction = battler.get_next_attacking_action(closestAttackRoute)
                realAction = player.try_make_decision(attackAction)

                #
                # 判断自己的下一步是否为敌人开路
                #-------------------------
                # 如果自己下一个行为是射击，然后所射掉的块为敌人进攻路线上的块
                # 那么将这个动作转为移动或者停止
                #
                # TODO:
                #   这个动作是有条件的，通常认为是，块就处在敌人的周围，我将块打破后
                #   敌人有炮，我不能马上移到块的，这样就可能让敌人过掉，在这种情况下避免开炮
                #
                #   TODO:
                #     不能被过掉的情况不准确！只有不再在同一直线的情况下才需要判断 5ce444a8d2337e01c7a5eaea
                #     如果两者处在同一条直线，假如双方都射击，那么下一回合就直接相遇，并不会出现被对方过掉的情况
                #
                if (not battler.on_the_same_line_with(oppBattler)
                    and Action.is_shoot(realAction)
                    and battler.will_destroy_a_brick_if_shoot(realAction) # 下一步将会打掉一个墙
                    ):
                    field = battler.get_destroyed_fields_if_shoot(realAction)[0]
                    enemyAttackRoute = oppBattler.get_shortest_attacking_route()
                    if enemyAttackRoute.has_block(field): # 打掉的 Brick 在敌人进攻路线上
                        #
                        # 再尝试模拟，是否会导致上述情况
                        #
                        _dontShoot = False
                        with outer_label() as OUTER_BREAK:
                            for enemyMoveAction in oppBattler.get_all_valid_actions():
                                # 一回合假设我方射击，敌人任意行为
                                with map_.simulate_multi_actions((battler, realAction), (oppBattler, enemyMoveAction)):
                                    moveAction = realAction - 4
                                    # 二回合假设我方移动，敌人射击
                                    for enemyShootAction in oppBattler.get_all_valid_shoot_actions(): # 自动判断是否可射击
                                        with map_.simulate_multi_actions((battler, moveAction), (oppBattler, enemyShootAction)):
                                            if battler.destroyed: # 然后这回合我方坦克挂了
                                                _dontShoot = True
                                                raise OUTER_BREAK

                        if _dontShoot:
                            player.set_status(Status.ACTIVE_DEFENSIVE)
                            return player.try_make_decision(moveAction) # 移动/停止

                # 否则直接采用主动防御的进攻策略
                #
                # TODO:
                #   这是个糟糕的设计，因为这相当于要和下方的进攻代码重复一遍
                #
                if battler.is_in_our_site():  # 只有在我方地盘的时候才触发
                    #
                    # 首先实现禁止随便破墙
                    #
                    if Action.is_shoot(realAction):
                        #
                        # 敌人处在墙后的水平路线上，并且与墙的间隔不超过 1 个空格 5cd33a06a51e681f0e91de95
                        # 事实上 1 个空格是不够的！ 5cd35e08a51e681f0e92182e
                        #
                        enemy = battler.get_enemy_behind_brick(realAction, interval=-1)
                        if enemy is not None:
                            player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)
                            player.set_status(Status.ACTIVE_DEFENSIVE)
                            return Action.STAY
                        #
                        # 敌人下一步可能移到墙后面
                        #
                        for moveAction in oppBattler.get_all_valid_move_actions():
                            with map_.simulate_one_action(oppBattler, moveAction):
                                if battler.get_enemy_behind_brick(realAction, interval=-1) is not None: # 此时如果直接出现在墙的后面
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return Action.STAY


                    if Action.is_stay(realAction):
                        # (inserted) 主动打破僵局：因为遇到敌人，为了防止被射杀而停留
                        # 注：
                        #   这段代码复制自下方的侵略模式
                        #--------------------------
                        if Action.is_move(attackAction):
                            if player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1): # 即将停留第二回合
                                oppPlayer = Tank2Player(oppBattler)
                                if (Action.is_move(oppPlayer.get_previous_action(back=1))
                                    and battler.get_manhattan_distance_to(oppBattler) == 2
                                    ): # 这种情况对应着对方刚刚到达拐角处，这种情况是有危险性的，因此再停留一回合 5cd4045c86d50d05a00840e1
                                    pass
                                elif oppBattler.canShoot: # 当回合可以射击，并且我上回合停留，因此敌人上回合可以射击
                                    # 说明敌人大概率不打算攻击我
                                    player.set_status(Status.ACTIVE_DEFENSIVE)
                                    return attackAction

                        player.set_status(Status.PREVENT_BEING_KILLED) # 否则标记为防止被杀，用于上面的触发

                    player.set_status(Status.ACTIVE_DEFENSIVE)
                    return realAction

#{ END 'decision/single/active_defense.py' }#



#{ BEGIN 'decision/single/marching.py' }#

class MarchingDecision(SingleDecisionMaker):
    """
    行军策略
    -------------------------

    当身边没有和任何敌人正面遭遇的时候，尝试寻找最佳的进攻行为

    1. 进攻
    2. 不会主动破墙
    3. 遇到僵局，会在指定回合后自动打破僵局
    4. 遇到有风险的路径导致需要停止不前的，会考虑寻找相同长度但是安全的路径，并改变方向
    5. ......

    """
    def _make_decision(self):

        player   = self._player
        signal   = self._signal
        map_     = player._map
        tank     = player.tank
        battler  = player.battler
        teammate = player.teammate

        Tank2Player = type(player)
        BattleTank  = type(battler)


        # (inserted) 强攻信号
        #-------------------------
        if signal == Signal.FORCED_MARCH:
            attackAction = battler.get_next_attacking_action() # 应该是移动行为，且不需检查安全性
            player.set_status(Status.READY_TO_FORCED_MARCH)
            return ( attackAction, Signal.READY_TO_FORCED_MARCH )


        oppTank = battler.get_nearest_enemy()
        oppBattler = BattleTank(oppTank)
        oppPlayer  = Tank2Player(oppBattler)

        myRoute = battler.get_shortest_attacking_route()
        oppRoute = oppBattler.get_shortest_attacking_route()
        # assert not myRoute.is_not_found() and not oppRoute.is_not_found(), "route not found" # 一定能找到路
        if myRoute.is_not_found() or oppRoute.is_not_found():
            # 可能出现这种队友堵住去路的及其特殊的情况！ 5cdde41fd2337e01c79f1284
            allowedDelay = 0
        else:
            leadingLength = oppRoute.length - myRoute.length

            if leadingLength <= 0:
                allowedDelay = 0 # 不必别人领先的情况下，就不要 delay 了 ...
            else:
                allowedDelay = leadingLength # 允许和对手同时到达，但由于我方先手，实际上应该是领先的

        #
        # 在我方地盘时，优先从边路攻击
        # 到达敌方场地，优先从中路攻击
        #
        # 5cde18e7d2337e01c79f47c8
        #
        isMiddleFirst = False
        # isMiddleFirst = battler.is_in_enemy_site()
        #
        # TODO:
        #   不要采用中路优先的搜索，否则容易打出狭路，然后因为敌人对自己存在威胁而停止不前！
        #   5ce48c2fd2337e01c7a6459b

        isXAxisFirst = False
        #
        # 如果我方两架坦克都到达了敌方基地，处于双方均不回头的局面 5cec9157641dd10fdcc5f30d
        # 那么可以采用 x-axis-first 以更好地触发团队合作，因为它优先选择拆除 x = 4 的墙
        #
        _allPlayers = [ player, teammate, *player.opponents ]
        if (all( _player.battler.is_in_enemy_site(include_midline=True) for _player in _allPlayers )
            and all( not _player.battler.has_enemy_around() for _player in _allPlayers )
            ): # 如果双方都处在对方基地，并且都没有遭遇到敌人
            isMiddleFirst = True # 想要使用 x-axis-first 必须首先 middle-first
            isXAxisFirst = True

        if battler.is_in_our_site():
            #
            # 在我方基地的时候，不要评估敌人对攻击路线的干扰，而是优先采用边路优先的搜索。这样可能和敌人相撞，
            # 但至少可以平局。如果在我方基地就开始衡量敌人的干扰，那么敌人绕边路的时候我方可能会选择中路，
            # 这种情况下可能会被另一边的敌人干扰，出现一牵二的局面。
            #
            # 还可能遇到一种很糟糕的情况，就是我方为了绕开敌人而选择了一条比最短路线要长的路，这种情况下
            # 可能我方最终就会落后与对方，这样如果还绕过了敌人，那就根本没法拦截了，到最后肯定是输。
            #
            # TODO:
            # ----------------------
            # 这个影响对于bot的侵略性影响非常大，因为很容易因此和对方平局。并且边路分拆难以触发合作拆家，
            # 进攻优势会被削弱。也许可以一牵二的情况进行特判，其他情况继续绕路？
            # 也许需要根据情况进行判定，毕竟一牵二的情况和绕路拆家结果反而赢了的情况是有的，而且似乎都不少见
            #
            routes = battler.get_all_shortest_attacking_routes(delay=allowedDelay, middle_first=isMiddleFirst, x_axis_first=isXAxisFirst)
        else:
            routes = sorted( battler.get_all_shortest_attacking_routes(delay=allowedDelay, middle_first=isMiddleFirst, x_axis_first=isXAxisFirst),
                                key=lambda r: estimate_enemy_effect_on_route(r, player) )

        route = None # 这回合的进攻路线
        returnAction = Action.STAY # 将会返回的行为，默认为 STAY

        #
        # 对于最优方案的缓存，用于判断次优行为是否合理
        # 没事老回头实在是太蠢了！ 5cee6790641dd10fdcc8de2c
        # 有路也不是这样走啊！
        #
        _firstAttackAction = None         # 第一条路线给出的进攻行为
        _firstRealAction = None           # 第一条路线下玩家真实决策的而行为
        _firstPreventBeingKilled = False  # 第一个进攻行为是否因为受到敌人拦截而受阻
        _firstStatus = None               # 缓存第一次决策时的状态
        _isFirstRoute = False             # 当前是否为第一条路径
        _firstRoute = None                # 缓存第一条路径

        with outer_label() as OUTER_BREAK:
            #
            # TODO:
            #   仅仅在此处综合考虑路线长度和敌人的影响，有必要统一让所有尝试获得下一步行为的函数都
            #   以于此处相同的方式获得下一攻击行为
            #
            # for route in battler.get_all_shortest_attacking_routes(): # 目的是找到一个不是停留的动作，避免浪费时间
            # for route in sorted_routes_by_enemy_effect(
            #                 battler.get_all_shortest_attacking_routes(delay=allowedDelay), player ):
            # for route in sorted( battler.get_all_shortest_attacking_routes(delay=allowedDelay, middle_first=isMiddleFirst, x_axis_first=isXAxisFirst),
            #                         key=lambda r: estimate_enemy_effect_on_route(r, player) ):
            _cachedAttackActions = set() # 缓存已经考虑过的结果
            for _idx, route in enumerate(routes): # 引入 idx 用于判断是第几个路线
                # 首先清除可能出现的状态，也就是导致 stay 的状况 ？？？？？
                _isFirstRoute = ( _idx == 0 )

                if _idx == 1: # 恰好过了第二回合
                    _firstStatus = player.get_status().copy() # 确保所有 continue 语句设置的 status 都可以在这里被捕获

                player.remove_status(Status.WAIT_FOR_MARCHING,
                                     Status.PREVENT_BEING_KILLED,
                                     Status.HAS_ENEMY_BEHIND_BRICK)

                attackAction = battler.get_next_attacking_action(route)

                if _isFirstRoute: # 缓存行为和路线
                    _firstAttackAction = attackAction
                    _firstRoute = route

                if attackAction in _cachedAttackActions: # 缓存攻击行为，避免重复判断
                    continue
                _cachedAttackActions.add(attackAction)

                if Action.is_stay(attackAction): # 下一步是停留，就没必要过多判断了
                    returnAction = attackAction
                    raise OUTER_BREAK

                realAction = player.try_make_decision(attackAction)

                if _isFirstRoute: # 缓存真实判断
                    _firstRealAction = realAction

                # debug_print(player, attackAction, realAction)

                if Action.is_stay(realAction): # 存在风险
                    if Action.is_move(attackAction):

                        # 特殊情况，如果下下回合就要打掉对方基地
                        # 那就没必要乱跑了 5cddde4dd2337e01c79f0ba3
                        #
                        if battler.is_face_to_enemy_base():
                            returnAction = realAction
                            raise OUTER_BREAK

                        # (inserted) 主动打破僵局：因为遇到敌人，为了防止被射杀而停留
                        # 注：
                        #   在上方的主动防御模式里还有一段和这里逻辑基本一致的代码
                        #--------------------------
                        if (player.has_status_in_previous_turns(Status.WAIT_FOR_MARCHING, turns=1)
                            and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1)
                            ): # 即将停留第二回合
                            riskyBattler = player.get_risky_enemy()
                            riskyPlayer = Tank2Player(riskyBattler)
                            #
                            # 判断敌人不会攻击我的标准
                            #
                            # 1. 敌人当前回合可以射击
                            # 2。 敌人上回合也可以射击
                            # 3. 敌人上回合与上上回合的行为相同，也就是已经连续移动了两个回合或者等待了两个回合
                            #    这个补充条件非常重要 5cde71a4d2337e01c79f9a77
                            #
                            #    TODO:
                            #       这个条件仍然不对！！ 5ce220add2337e01c7a38462
                            #
                            if (riskyBattler.canShoot # 当回合可以射击
                                and not riskyPlayer.has_status_in_previous_turns(Status.RELOADING) # 上回合也可以射击
                                and riskyPlayer.get_previous_action(back=1) == riskyPlayer.get_previous_action(back=2)
                                ): # 说明敌人大概率不打算攻击我
                                if (Action.is_move(riskyPlayer.get_previous_action(back=1))
                                    and battler.get_manhattan_distance_to(riskyBattler) == 2
                                    ): # 这种情况对应着对方刚刚到达拐角处，这种情况是有危险性的，因此再停留一回合 5cd4045c86d50d05a00840e1
                                    player.set_status(Status.WAIT_FOR_MARCHING)
                                    player.set_status(Status.PREVENT_BEING_KILLED)
                                    pass
                                else:
                                    # TODO:
                                    #   此处需要检查是否应该预先破墙 5ce21ba2d2337e01c7a37dbd
                                    #
                                    player.set_status(Status.KEEP_ON_MARCHING)
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
                                action = player.try_make_decision(battler.shoot_to(field))
                                if Action.is_shoot(action):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    player.set_status(Status.WAIT_FOR_MARCHING)
                                    player.set_status(Status.PREVENT_BEING_KILLED)
                                    returnAction = action
                                    raise OUTER_BREAK
                        #
                        # 如果能摧毁的是基地外墙，仍然选择攻击
                        # 因为在攻击后可能可以给出更加短的路线
                        #
                        for field in fields:
                            if battler.check_is_outer_wall_of_enemy_base(field):
                                action = player.try_make_decision(battler.shoot_to(field))
                                if Action.is_shoot(action):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    player.set_status(Status.WAIT_FOR_MARCHING)
                                    player.set_status(Status.PREVENT_BEING_KILLED)
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
                        if (not player.has_status(Status.DEFENSIVE)  # 防御性无效
                            and battler.is_in_enemy_site()  # 只有在对方基地的时候才有效
                            ):
                            for field in fields:
                                if (isinstance(field, BrickField)
                                    and battler.get_manhattan_distance_to(field) == 2 # 距离为 2 相当于土墙
                                    and battler.canShoot
                                    ):
                                    # 这个信号是他现在的真实体现，可以用来触发团队破墙信号
                                    player.set_status(Status.WAIT_FOR_MARCHING)
                                    player.set_status(Status.PREVENT_BEING_KILLED)
                                    player.set_status(Status.READY_TO_CLEAR_A_ROAD_FIRST)
                                    returnAction = battler.shoot_to(field)
                                    raise OUTER_BREAK


                    elif Action.is_shoot(attackAction):
                        # 如果为射击行为，检查是否是墙后敌人造成的
                        enemy = battler.get_enemy_behind_brick(attackAction, interval=-1)
                        if enemy is not None:
                            player.set_risky_enemy(enemy) # 额外指定一下，确保是这个敌人造成的
                            player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)

                        #
                        # 强攻行为，如果出现这种情况，双方均在拆家，但是对方坦克下一步有可能移到我方坦克后方
                        # 对于这种情况，大部分人应该选择继续进攻，同时绕开麻烦，因为进攻的时候还考虑击杀敌人
                        # 一般会延误战机。这种情况下应该判定为敌方坦克不会来尝试击杀我方坦克，那么就继续攻击
                        # 5ce57074d2337e01c7a7b128
                        #
                        oppBattler = player.get_risky_enemy()
                        if (battler.is_in_enemy_site() # 双方均在对方基地方时才触发
                            and oppBattler.is_in_enemy_site()
                            ):
                            #
                            # 现在尝试看对方是否能够找到一条不受到我方坦克影响的最短攻击路线
                            # 通常应该是可以找到的
                            #
                            _consideredActions = set() # 缓存已经考虑过的行为
                            for route in oppBattler.get_all_shortest_attacking_routes():
                                _action = oppBattler.get_next_attacking_action()
                                if _action in _consideredActions:
                                    continue
                                _consideredActions.add(_action)
                                with map_.simulate_one_action(oppBattler, _action):
                                    if not battler.has_enemy_around():
                                        # 说明找到了一条可以躲开我方坦克的路线
                                        player.set_status(Status.KEEP_ON_MARCHING)
                                        returnAction = attackAction
                                        raise OUTER_BREAK


                    #
                    # 否则停止不前
                    # 此时必定有 riskyEnemy
                    #
                    player.set_status(Status.WAIT_FOR_MARCHING) # 可能触发 Signal.PREPARE_FOR_BREAK_BRICK 和 Signal.FORCED_MARCH
                    player.set_status(Status.PREVENT_BEING_KILLED) # TODO: 这个状态是普适性的，希望在上面的各种情况中都能补全

                    if _isFirstRoute:
                        _firstPreventBeingKilled = True # 缓存状态，仅仅在因为防止被杀而停留的状态下缓存，其他情况不算
                        _firstStatus = player.get_status().copy() # 结束时常规地要复制一次，避免没有第二条路的情况

                    returnAction = Action.STAY
                    continue # 停留动作，尝试继续寻找

                # 对于移动行为，有可能处于闪避到远路又回来的僵局中 5cd009e0a51e681f0e8f3ffb
                # 因此在这里根据前期状态尝试打破僵局
                #----------------------------------
                if (player.has_status_in_previous_turns(Status.WILL_DODGE_TO_LONG_WAY, turns=1) # 说明上回合刚闪避回来
                    and Action.is_move(realAction) # 然后这回合又准备回去
                    ):
                    # TODO:
                    #   此处是否有必要进一步检查两次遇到的敌人为同一人？
                    #
                    #
                    # 首先考虑前方相距一格处是否有土墙，如果有，那么就凿墙 5cd009e0a51e681f0e8f3ffb
                    #
                    if battler.will_destroy_a_brick_if_shoot(realAction):
                        field = battler.get_destroyed_fields_if_shoot(realAction)[0]
                        if (not battler.is_in_our_site(field) # 这个 brick 必须不在我方基地！
                            and battler.get_manhattan_distance_to(field) == 2
                            and battler.canShoot
                            ):
                            player.set_status(Status.KEEP_ON_MARCHING) # 真实体现
                            returnAction = battler.shoot_to(field)
                            raise OUTER_BREAK

                    #player.add_label(Label.ALWAYS_DODGE_TO_LONG_WAY) # 如果能够运行到这里，就添加这个标记


                # 预判一步，如果下一步会遇到敌人，并且不得不回头闪避的话，就考虑先摧毁与自己中间相差一格的墙（如果存在）
                # 类似于主动防御的情况
                #
                if Action.is_move(realAction):

                    if battler.is_face_to_enemy_base(ignore_brick=True):
                        # 如果已经和基地处在同一直线上
                        with map_.simulate_one_action(battler, realAction):
                            if not battler.is_face_to_enemy_base(ignore_brick=True):
                                returnAction = Action.STAY # 如果移动后不再面对敌人基地，那么就不移动
                                raise OUTER_BREAK

                    if (not player.has_status(Status.DEFENSIVE) #　防御性无效
                        and battler.is_in_enemy_site()  # 只有在敌方地盘时才有效！
                        and battler.will_destroy_a_brick_if_shoot(realAction) # 如果下回合能射掉一个墙
                        ):
                        _needToBreakWallFirst = True

                        with map_.simulate_one_action(battler, realAction):
                            enemies = battler.get_enemies_around()
                            if len(enemies) == 0: # 没有敌人根本不需要预判
                                _needToBreakWallFirst = False
                            else:
                                with outer_label() as OUTER_BREAK_2:
                                    route1 = battler.get_shortest_attacking_route()
                                    for enemy in battler.get_enemies_around():
                                        for action in battler.try_dodge(enemy):
                                            with map_.simulate_one_action(battler, action):
                                                route2 = battler.get_shortest_attacking_route() # 只有 route1 为 delay = 0 的选择才可比较
                                                if route2.length <= route1.length:  # 如果存在着一种闪避方法使得闪避后线路长度可以不超过原线路长度
                                                    _needToBreakWallFirst = False  # 那么就不破墙
                                                    raise OUTER_BREAK_2

                        if _needToBreakWallFirst: # 现在尝试破墙
                            shootAction = realAction + 4
                            for field in battler.get_destroyed_fields_if_shoot(shootAction):
                                if isinstance(field, BrickField):
                                    if battler.get_manhattan_distance_to(field) == 2: # 距离为 2 的土墙
                                        if battler.canShoot:
                                            player.set_status(Status.WAIT_FOR_MARCHING)
                                            player.set_status(Status.READY_TO_CLEAR_A_ROAD_FIRST)
                                            returnAction = shootAction # 不检查安全性
                                            raise OUTER_BREAK

                        if (_needToBreakWallFirst
                            and not battler.canShoot # 需要射击但是暂时没有炮弹，那么就等待
                            ):
                            player.set_status(Status.WAIT_FOR_MARCHING)
                            returnAction = Action.STAY
                            continue

                #
                # 考虑这样一种情况，如果下回合我可以射击且对方可以射击，我们中间差两个墙，如果我方不射击
                # 对方可能就会压制过来，这样就很亏，所以当双方都有炮且两者间差一个墙的时候，我方优先射击
                # 5cea974dd2337e01c7add31f
                #
                if (( player.has_status(Status.AGGRESSIVE) or player.has_status(Status.STALEMENT) )
                    and Action.is_move(realAction)
                    and battler.canShoot
                    ):
                    shootAction = realAction + 4
                    _hasEnemyBehindTwoBricks = False
                    oppBattler = None
                    destroyedFields = battler.get_destroyed_fields_if_shoot(shootAction)
                    if (len(destroyedFields) == 1 and isinstance(destroyedFields[0], BrickField) # 前方是墙
                        and battler.get_enemy_behind_brick(shootAction, interval=-1) is None     # 现在墙后无人
                        ):
                        with map_.simulate_one_action(battler, shootAction):
                            destroyedFields = battler.get_destroyed_fields_if_shoot(shootAction)
                            if len(destroyedFields) == 1 and isinstance(destroyedFields[0], BrickField): # 现在前面还有墙
                                enemy = battler.get_enemy_behind_brick(shootAction, interval=-1)
                                if enemy is not None: # 此时墙后有人
                                    _hasEnemyBehindTwoBricks = True
                                    oppBattler = BattleTank(enemy)

                    if _hasEnemyBehindTwoBricks:
                        if oppBattler.canShoot: # 此时对方也可以射击
                            player.set_status(Status.KEEP_ON_MARCHING)
                            returnAction = shootAction # 那么我方这回合优先开炮，避免随后和对方进入僵持阶段
                            raise OUTER_BREAK


                #
                # move action 在这之前必须要全部处理完！
                #

                #
                # 侵略模式下优先射击，如果能够打掉处在最短路线上的墙壁
                #-------------------
                if (player.has_status(Status.AGGRESSIVE)
                    and Action.is_move(realAction)
                    and battler.canShoot
                    ):
                    shootAction = realAction + 4
                    for field in battler.get_destroyed_fields_if_shoot(shootAction):
                        if isinstance(field, BrickField) and field.xy in route: # 能够打掉一个处于最短路线上的土墙
                            action = player.try_make_decision(shootAction)
                            if Action.is_shoot(action):
                                player.set_status(Status.KEEP_ON_MARCHING)
                                realAction = shootAction # 注意：这里修改了 realAction 方便后续判断，但是这是非常不好的一个做法
                                break

                #
                # 禁止随便破墙！容易导致自己陷入被动！
                #
                if Action.is_shoot(realAction):
                    #
                    # 敌人处在墙后的水平路线上，并且与墙的间隔不超过 1 个空格 5cd33a06a51e681f0e91de95
                    # 事实上 1 个空格是不够的！ 5cd35e08a51e681f0e92182e
                    #
                    _shouldStay = False
                    oppBattler  = None

                    enemy = battler.get_enemy_behind_brick(realAction, interval=-1)
                    if enemy is not None: # 墙后有人，不能射击
                        # 否则就等待
                        #---------------
                        player.set_risky_enemy(enemy) # 设置这个敌人！
                        player.set_status(Status.HAS_ENEMY_BEHIND_BRICK)
                        player.set_status(Status.WAIT_FOR_MARCHING)
                        _shouldStay = True

                    #
                    # 敌人下一步可能移到墙后面
                    #
                    if not _shouldStay:
                        with outer_label() as OUTER_BREAK_2:
                            for oppBattler in [ _oppPlayer.battler for _oppPlayer in player.opponents ]:
                                if oppBattler.destroyed:
                                    continue
                                for moveAction in oppBattler.get_all_valid_move_actions():
                                    with map_.simulate_one_action(oppBattler, moveAction):
                                        enemy = battler.get_enemy_behind_brick(realAction, interval=-1)
                                        if enemy is not None: # 此时如果直接出现在墙的后面
                                            player.set_status(Status.WAIT_FOR_MARCHING)
                                            player.set_status(Status.ENEMY_MAY_APPEAR_BEHIND_BRICK)
                                            player.set_risky_enemy(enemy) # 仍然将其设置为墙后敌人
                                            _shouldStay = True
                                            raise OUTER_BREAK_2

                    #
                    # 并不是一定不能破墙，需要检查敌人是否真的有威胁
                    #
                    # 1. 和队友相遇的敌人可以忽略 5ce209c1d2337e01c7a36a0a
                    # 2. 和队友隔墙僵持的敌人可以忽略（这种情况非常有可能) 5ce5678ed2337e01c7a79ace
                    # 3. 对手正在和队友僵持的敌人可以忽略 5ce70df6d2337e01c7a98926
                    # 4. 如果对手威胁我的位置他曾经到过，那么可以忽略 5ce266a1d2337e01c7a3cc90
                    #
                    if _shouldStay and oppBattler is not None:
                        teammateBattler = teammate.battler
                        oppTank = oppBattler.tank

                        # 考虑两人相对
                        for enemy in teammateBattler.get_enemies_around():
                            if enemy is oppTank: # 被队友牵制的敌人可以忽略
                                _shouldStay = False
                                break

                        # 考虑是否隔墙僵持
                        _action = teammateBattler.get_next_attacking_action()
                        if not Action.is_stay(_action):
                            enemy = teammateBattler.get_enemy_behind_brick(_action, interval=-1)
                            if enemy is oppTank: # 和队友隔墙僵持的敌人可以忽略
                                _shouldStay = False

                        # 考虑是否和队友僵持
                        if teammateBattler.get_manhattan_distance_to(oppBattler) == 2:
                            _action = oppBattler.get_next_attacking_action()
                            with map_.simulate_one_action(oppBattler, _action): # 模拟一步后和队友相遇
                                if teammateBattler.get_manhattan_distance_to(oppBattler) == 1:
                                    _shouldStay = False

                        #
                        # 如果敌人威胁我的位置它曾经到过（这种情况实际上包含了第三点）
                        #
                        # 先找到威胁我方坦克的位置
                        _enemyRiskySite = None # (x, y)
                        with map_.simulate_one_action(battler, realAction):
                            for _action in oppBattler.get_all_valid_move_actions():
                                with map_.simulate_one_action(oppBattler, _action):
                                    if battler.on_the_same_line_with(oppBattler):
                                        _enemyRiskySite = oppBattler.xy
                                        break

                        #assert _enemyRiskySite is not None # 一定会找到？

                        enemyAttackingRoute = oppBattler.get_shortest_attacking_route()
                        #
                        # 不在敌人的进攻路线上，这样才算是已经走过，否则可以认为他在晃墙？
                        # 5cec129e4742030582fac36d
                        #
                        if not _enemyRiskySite in enemyAttackingRoute:
                            with map_.auto_undo_revert() as counter:
                                while map_.revert(): # 回滚成功则 True
                                    counter.increase()
                                    if oppBattler.xy == _enemyRiskySite: # 他曾经到过这个地方
                                        _shouldStay = False
                                        break

                    if (_shouldStay
                        and player.has_status(Status.ENEMY_MAY_APPEAR_BEHIND_BRICK)
                        ): # 不能在这种情况下破墙！ 5cec129e4742030582fac36d
                        returnAction = Action.STAY
                        continue

                    if _shouldStay:
                        # 先尝试 shoot 转 move
                        #---------------
                        if Action.is_shoot(realAction):
                            moveAction = realAction - 4
                            action = player.try_make_decision(moveAction)
                            if Action.is_move(action):
                                returnAction = action
                                break

                    if _shouldStay: # 否则 stay
                        returnAction = Action.STAY
                        continue

                #
                # (inserted) 打破老是回头的僵局
                #
                # 尝试向着两边闪避 5ced9540641dd10fdcc79752
                #
                if (oppBattler is not None # 好吧 ... 不加这个可能过不了自动测试 -> TODO: 也许我们不应该再替对方决策一遍？
                    and player.has_label(Label.ALWAYS_BACK_AWAY)
                    and not battler.is_in_our_site(include_midline=True) # 限制为严格地不在我方基地
                    ):
                    for action in battler.try_dodge(oppBattler):
                        _realAction = player.try_make_decision(action)
                        if not Action.is_stay(_realAction): # 可走的路线，那么直接闪避
                            player.set_status(Status.TRY_TO_BREAK_ALWAYS_BACK_AWAY)
                            player.remove_labels(Label.ALWAYS_BACK_AWAY) # 那么就打破了这个状态
                            realAction = _realAction # 并将闪避方向作为这回合的攻击方向
                            break

                # 否则继续攻击
                player.set_status(Status.KEEP_ON_MARCHING)
                returnAction = realAction
                raise OUTER_BREAK

            # endfor
        # endwith

        player.set_current_attacking_route(route) # 缓存攻击路线

        #
        # 现在判断是否是第一条路线，并考虑它的合理性！
        #
        # 乱回头实在是太蠢了！ 5cee6727641dd10fdcc8dd96 -> 5cee6e3d641dd10fdcc8e8cf
        #
        if (not _isFirstRoute # 选的是非第一条路线
            and _firstPreventBeingKilled # 不选一条的原因是为了防止被杀
            and Action.is_move(realAction) # 这条路线给出的行为是移动
            and Action.is_move(_firstAttackAction) # 第一个进攻路线也是移动
            and Action.is_opposite(realAction, _firstAttackAction) # 于是这条路线给出的移动方向是远离进攻路线的方向！
            ): # 这种情况下应该停下来！
            returnAction = Action.STAY
            player.remove_status(Status.KEEP_ON_MARCHING)
            player.set_status(*_firstStatus)
            player.set_current_attacking_route(_firstRoute)

        # 找到一个侵略性的行为
        if not Action.is_stay(returnAction):
            return returnAction


        #
        # 否则返回 STAY
        # 此处查找是否和第一条路线的决策结果一致，如果一致，那么就将第一次决策下的各种状态还原
        #
        if (_firstRealAction is not None
            and Action.is_stay(_firstRealAction)
            ):
            if _firstStatus is not None:
                player.set_status(*_firstStatus)
            player.set_current_attacking_route(_firstRoute)

        return Action.STAY

#{ END 'decision/single/marching.py' }#



#{ BEGIN 'decision/team/individual.py' }#

class IndividualTeamDecision(TeamDecisionMaker):
    """
    两人分别单独地进行决策，团队决策的起点

    """
    def _make_decision(self):

        team = self._team
        player1, player2 = team.players

        action1, _ = player1.make_decision()
        action2, _ = player2.make_decision()

        return [ action1, action2 ]

#{ END 'decision/team/individual.py' }#



#{ BEGIN 'decision/team/vital.py' }#

class VitalTeamDecision(TeamDecisionMaker):
    """
    将关键的个人决策设置为团队决策，个人决策即为团队最优决策，
    低优先级决策者不可对其进行协调

    """
    def _make_decision(self):

        team = self._team

        for player in team.players:
            if (   player.has_status(Status.SACRIFICE_FOR_OUR_BASE)   # 准备为防御基地牺牲
                or player.has_status(Status.BLOCK_ROAD_FOR_OUR_BASE)  # 准备为防御基地堵路
                or player.has_status(Status.READY_TO_ATTACK_BASE)     # 准备攻击敌方基地
                or player.has_status(Status.READY_TO_KILL_ENEMY)      # 准备击杀敌人
                ):
                # TODO: 牺牲攻击局，可能需要考虑一下闪避 5ccca535a51e681f0e8c7131
                action = player.get_current_decision()
                player.set_team_decision(action) # 将个人决策设置为团队决策

        return [ player.get_current_decision() for player in team.players ]

#{ END 'decision/team/vital.py' }#



#{ BEGIN 'decision/team/leave_teammate.py' }#

class LeaveTeammateTeamDecision(TeamDecisionMaker):
    """
    和队友打破重叠的团队决策

    己方两个坦克重叠在一起这种事情实在是太愚蠢了 ...

    """
    def _make_decision(self):

        team = self._team
        player1, player2 = team.players
        returnActions = [ player.get_current_decision() for player in team.players ]

        if player1.defeated or player2.defeated: # 有队友已经挂了，那就不需要考虑这个情况了
            return returnActions

        if player1.tank.xy == player2.tank.xy:

            if len([ action for action in returnActions if Action.is_move(action) ]) == 1:
                pass # 一人移动一人非移动，那么是合理的

            elif (
                all( Action.is_move(action) for action in returnActions )
                and returnActions[0] != returnActions[1]
                ): # 两人均为移动，但是两人的移动方向不一样，这样也是可以的
                pass

            elif all([ player.has_team_decision() for player in team.players ]):
                pass # 两者都拥有团队命令

            else:
                # 两个队员可以认为是一样的，因此任意选择一个就好
                if player1.has_team_decision():
                    player, idx = (player2, 1)
                else:
                    player, idx = (player1, 0)

                with player.create_snapshot() as manager:
                    action3, signal3 = player.make_decision(Signal.SHOULD_LEAVE_TEAMMATE)
                    if signal3 == Signal.READY_TO_LEAVE_TEAMMATE:
                        returnActions[idx]  = action3
                        player.set_team_decision(action3)
                        manager.discard_snapshot() # 保存更改

        return returnActions

#{ END 'decision/team/leave_teammate.py' }#



#{ BEGIN 'decision/team/forced_attack.py' }#

class ForcedAttackTeamDecision(TeamDecisionMaker):
    """
    强攻信号
    ----------------

    为了解决单人决策行为过于保守的问题

    在攻击过程中，一些所谓的有潜在危险的行为，实际上一点危险都没有,但是为了防止出错，就原地等待，
    这反而是贻误了战机，甚至最后还要匆忙转攻为守，实际上根本就防不住

    所以应该根据战场形势分析潜在风险究竟有多大，如果实际上是没有风险的，就发动强攻信号，让攻击者
    保持进攻，而不去过分规避风险

    如下情况是值得发动强攻信号的：
    1. 侵略/僵持模式，出现了停止前进，防止被杀的状况
       - 敌人正在和队友交火，敌人此回合可以射击，但是下回合必定会攻击队友
       - 敌人正在和队友隔墙僵持，敌人可以射击，但是他并不攻击，多半是为了拖延战局
       - 敌人正在和队友重叠，敌人可以射击，但是他一直在等待队友决策
    2. 侵略/僵持模式，出现了停止前进，两方均越过了中线，对方明显不会回头，不想防你

    """
    def _make_decision(self):

        team = self._team
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:
            action = player.get_current_decision()

            if player.has_team_decision() or player.defeated:
                continue

            if (   player.has_status(Status.AGGRESSIVE)  # 侵略模式
                or player.has_status(Status.STALEMENT)   # 僵持模式
                ):
                if (action == Action.STAY # 但是出现了停止前进
                    and player.has_status(Status.WAIT_FOR_MARCHING)    # 等待行军
                    and player.has_status(Status.PREVENT_BEING_KILLED) # 是为了防止被杀
                    ):
                    _shouldForcedMarch = False

                    playerRiskyEnemyBattler = player.get_risky_enemy()
                    if playerRiskyEnemyBattler is None: # 说明是因为没有弹药？
                        continue
                    oppPlayer = Tank2Player(playerRiskyEnemyBattler)
                    teammate = player.teammate # 考虑队友和敌军的情况

                    #debug_print(player.get_risky_enemy())
                    #debug_print(teammate.get_risky_enemy())

                    # 敌人正在和队友交火
                    #------------------
                    # 这种情况直接前进
                    #
                    if (oppPlayer.has_status(Status.ENCOUNT_ENEMY)
                        and oppPlayer.has_status(Status.READY_TO_FIGHT_BACK)
                        and oppPlayer.get_risky_enemy() is teammate.battler
                        ): # 说明对方正准备和队友交火
                        _shouldForcedMarch = True

                    # 敌人正在和队友隔墙僵持
                    #----------------------
                    # 如果他们僵持了超过一回合以上
                    # 保守起见，等待一回合，如果对方并未攻击我，说明它更关心和队友僵持，或者故意在拖时间
                    #
                    # 那么可以直接进攻
                    #
                    elif (oppPlayer.has_status(Status.HAS_ENEMY_BEHIND_BRICK) # 僵持超过一回合
                        and oppPlayer.has_status_in_previous_turns(Status.HAS_ENEMY_BEHIND_BRICK, turns=1)
                        and oppPlayer.get_risky_enemy() is teammate.battler
                        and player.has_status_in_previous_turns(Status.WAIT_FOR_MARCHING, turns=1) # 已经等待了一回合
                        and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1)
                        ):
                        _shouldForcedMarch = True

                    # 敌人正在和队友重叠
                    #----------------------------
                    # 如果他们重叠不动超过一回合以上
                    # 保守起见，等待一回合，如果对方并未攻击我，说明它更关心和队友重叠
                    #
                    # 那么可以直接进
                    #
                    elif (oppPlayer.has_status(Status.OVERLAP_WITH_ENEMY) # 僵持超过一回合
                        and oppPlayer.has_status_in_previous_turns(Status.OVERLAP_WITH_ENEMY, turns=1)
                        and player.has_status_in_previous_turns(Status.WAIT_FOR_MARCHING, turns=1) # 已经等待了一回合
                        and player.has_status_in_previous_turns(Status.PREVENT_BEING_KILLED, turns=1)
                        ):
                        _shouldForcedMarch = True

                    # 双方均跨过中线
                    #-----------------------------
                    # 那么不再反击，直接进攻？
                    #
                    # TODO:
                    #   存在着一攻一守的 bot
                    #
                    if _shouldForcedMarch: # 建议强制行军

                        with player.create_snapshot() as manager:
                            action3, signal3 = player.make_decision(Signal.FORCED_MARCH)
                            if Signal.is_break(signal3):
                                continue
                            if signal3 == Signal.READY_TO_FORCED_MARCH:
                                returnActions[player.id] = action3
                                player.set_team_decision(action3)
                                player.set_status(Status.FORCED_MARCHING)
                                manager.discard_snapshot()

        return returnActions

#{ END 'decision/team/forced_attack.py' }#



#{ BEGIN 'decision/team/break_brick.py' }#

class BreakBrickTeamDecision(TeamDecisionMaker):
    """
    主动破墙的团队决策
    -----------------

    乱破墙是不可以的，单人不要随便破墙，但是有条件的破墙是可以的

    """
    def _make_decision(self):

        team = self._team
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:
            action = player.get_current_decision()

            if player.has_team_decision() or player.defeated:
                continue

            if (Action.is_stay(action)                                # 当前回合处于等待状态
                and player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)  # 墙后有人造成的
                and player.has_status(Status.WAIT_FOR_MARCHING)       # 因此等待行军
                #and not player.has_status(Status.DEFENSIVE) # 不要让防御性的队友随意破墙
                and not player.has_status(Status.RELOADING) # 目前有弹药
                # and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=1) # 改成一有机会就先留后路
                ):

                # 触发的条件是一方隔墙，队友因为这两个人的僵持受到牵制
                #----------------------------------------------------

                # 僵持方先破墙，留好后路
                #----------------------
                with player.create_snapshot() as manager:
                    action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_BRICK)
                    if Signal.is_break(signal3):
                        continue

                    if signal3 == Signal.READY_TO_PREPARE_FOR_BREAK_BRICK: # 下一步准备凿墙
                        returnActions[player.id] = action3
                        player.set_team_decision(action3)
                        manager.discard_snapshot()
                        continue # 至此该队员决策完成，等待它这回合凿墙

                    # elif signal3 == Signal.READY_TO_BREAK_BRICK:
                    # 否则将受到破墙信号，开始判断是否符合破墙条件

                    elif signal3 == Signal.READY_TO_BREAK_BRICK:
                        oppBattler = player.get_risky_enemy() # 获得墙后敌人
                        assert oppBattler is not None # 必定有风险敌人
                        oppPlayer = Tank2Player(oppBattler)

                        # playerIdx   = idx
                        # teammateIdx = 1 - idx
                        teammate = player.teammate

                        _shouldBreakBrick = False


                        if oppBattler.has_enemy_around(): # 发现敌人和队友相遇，立即破墙
                            _shouldBreakBrick = True

                        ''' 这个两个触发已经不再需要了 5ce217e8d2337e01c7a3790c

                        # TODO:
                        #   这种情况挺难遇到的，而且一旦遇到一般都为时过晚
                        #   应该要模拟地图预测一下，提前开一炮
                        #
                        if (teammate.has_status(Status.WAIT_FOR_MARCHING) # 队友等待
                            # and self.has_status_in_previous_turns(teammate, Status.WAIT_FOR_MARCHING, turns=1)
                            and teammate.has_status(Status.PREVENT_BEING_KILLED)   # 队友是为了防止被杀
                            ):
                            teammateRiskyEnemyBattler = teammate.get_risky_enemy()
                            playerRiskyEnemyBattler = player.get_risky_enemy() # 墙后敌人
                            if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                # 两者受到同一个敌人牵制，那么发动破墙信号
                                _shouldBreakBrick = True


                        elif ( teammate.has_status(Status.AGGRESSIVE)
                            or teammate.has_status(Status.STALEMENT)
                            ):
                            teammateAction = returnActions[ teammateIdx ]
                            if (Action.is_move(teammateAction) # 确保队友动作为移动
                                and teammate.has_status(Status.KEEP_ON_MARCHING) # 队友正在行军
                                ):
                                # 尝试模拟下一回合的队友状态，并让队友重新决策，查看他的状态
                                with map_.simulate_one_action(teammate, teammateAction):
                                    action4, _ = teammate.make_decision()
                                    if (teammate.has_status(Status.WAIT_FOR_MARCHING)
                                        and teammate.has_status(Status.PREVENT_BEING_KILLED)
                                        ): # 这个时候队友被阻拦
                                        teammateRiskyEnemyBattler = teammate.get_risky_enemy()
                                        playerRiskyEnemyBattler = player.get_risky_enemy()
                                        if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                            _shouldBreakBrick = True # 如果是因为对面墙的坦克在阻拦，那么马上破墙'''

                        #
                        # 如果遇到对手准备和队友对射 5cd364e4a51e681f0e921e7a
                        # 那么考虑直接破墙
                        #
                        # 敌方当前回合应该必定会还击，否则就失去了防御的意义
                        # 于是，随后就会遇到二对一且三方均没有炮弹
                        # 如果对方下回合不走，那么二打一直接干掉
                        # 如果对方下回合移动，那么攻击的队友就解除了威胁，可以继续前进
                        #
                        if (not teammate.has_status(Status.DEFENSIVE)
                            and teammate.has_status(Status.ENCOUNT_ENEMY)
                            and teammate.has_status(Status.READY_TO_FIGHT_BACK)
                            ):
                            teammateRiskyEnemyBattler = teammate.get_risky_enemy()
                            playerRiskyEnemyBattler = player.get_risky_enemy()
                            if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                _shouldBreakBrick = True


                        if _shouldBreakBrick:
                            returnActions[player.id] = action3
                            player.set_team_decision(action3)
                            manager.discard_snapshot()
                            continue


        return returnActions

#{ END 'decision/team/break_brick.py' }#



#{ BEGIN 'decision/team/back_to_help.py' }#

class BackToHelpTeamDecision(TeamDecisionMaker):
    """
    考虑一种墙后后退的逻辑 5cea650cd2337e01c7ad8de4
    这样可以制造二打一的局面

    TODO:
      回退后可能会造成 WITHDRAW 的情况出现 ?

    """
    def _make_decision(self):

        team = self._team
        map_ = team._map
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:
            action = player.get_current_decision()

            if player.has_team_decision() or player.defeated:
                continue

            teammate = player.teammate
            teammateBattler = teammate.battler
            if (player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)
                and teammate.has_status(Status.WITHDRAW)
                and teammate.has_status(Status.ENCOUNT_ENEMY)
                and (teammate.has_status(Status.READY_TO_FIGHT_BACK)
                    or teammate.has_status_in_previous_turns(Status.READY_TO_FIGHT_BACK, turns=1)
                    ) # 保持对射行为，
                      # TODO:
                      #   或许可以考虑用 对射状态描述撤退状态下的对射？
                ):
                battler = player.battler
                oppBattler = player.get_risky_enemy()
                if oppBattler is None: # 5cee87fc641dd10fdcc91b44 为何空指针 ???
                    continue
                oppPlayer = Tank2Player(oppBattler)
                teammateRiskyEnemyTank = oppPlayer.teammate.tank # 当前和我墙后僵持的敌人的队友
                if oppBattler is not None and teammateRiskyEnemyTank is not None: # 应该不会这样？
                    backAwayAction = battler.back_away_from(oppBattler)
                    _shouldBackAway = False
                    with map_.auto_revert() as counter:
                        while map_.is_valid_move_action(battler, backAwayAction):
                            map_.single_simulate(battler, backAwayAction)
                            counter.increase()
                            if teammateRiskyEnemyTank in battler.get_enemies_around():
                                _shouldBackAway = True
                                break

                    if _shouldBackAway:

                        with player.create_snapshot() as manager:
                            action3, signal3 = player.make_decision(Signal.SUGGEST_TO_BACK_AWAY_FROM_BRICK)
                            if Signal.is_break(signal3):
                                continue

                            if signal3 == Signal.READY_TO_BACK_AWAY_FROM_BRICK:
                                returnActions[player.id] = action3
                                player.set_team_decision(action3)
                                continue

        return returnActions

#{ END 'decision/team/back_to_help.py' }#



#{ BEGIN 'decision/team/prevent_team_hurt.py' }#

class PreventTeamHurtTeamDecision(TeamDecisionMaker):
    """
    防止队员自残
    --------------
    在决策链的最后，判断是否出现队友恰好打掉准备移动的队友的情况，并加以协调

    """
    def _make_decision(self):

        team = self._team
        map_ = team._map
        oppBase = map_.bases[1 - team.side]
        player1, player2 = team.players
        returnActions = [ player.get_current_decision() for player in team.players ]

        if player1.defeated or player2.defeated: # 有队友已经挂了，没必要考虑这个情况
            return returnActions

        action1, action2 = returnActions
        _mayShouldForcedStop = False

        if Action.is_shoot(action1) and Action.is_move(action2):
            shootAction = action1
            shootPlayer = player1
            moveAction  = action2
            movePlayer  = player2
            _mayShouldForcedStop = True
        elif Action.is_move(action1) and Action.is_shoot(action2):
            shootAction = action2
            shootPlayer = player2
            moveAction  = action1
            movePlayer  = player1
            _mayShouldForcedStop = True

        if _mayShouldForcedStop:
            moveBattler = movePlayer.battler
            shootBattler = shootPlayer.battler
            _shouldForcedStop = False
            with map_.simulate_one_action(moveBattler, moveAction):
                with map_.simulate_one_action(shootBattler, shootAction):
                    if moveBattler.destroyed: # 刚好把队友打死 ...
                        _shouldForcedStop = True

            if _shouldForcedStop:
                #
                # TODO:
                #   如何决策？
                #   改动射击和决策都有可能很危险
                #

                #
                # 这里先做一个特殊情况，那就是重叠攻击基地，这种情况将移动的队友视为不移动
                #
                # TODO:
                #   好吧，这种情况和主动和队友打破重叠的行为是相斥的 ...
                #
                '''if (moveBattler.xy == shootBattler.xy
                    and moveBattler.is_face_to_enemy_base(ignore_brick=False)
                    and shootBattler.is_face_to_enemy_base(ignore_brick=False)
                    ):
                    returnActions[movePlayer.id] = Action.STAY
                    hasTeamActions[movePlayer.id] = True'''


                #
                # 先判断这种情况 5ce92f70d2337e01c7abf587
                #-----------------
                #

                # 默认让射击队友停下
                #--------------------
                stayID = shootBattler.id
                stopPlayer = shootPlayer

                #
                # 以下情况，应该让 moveBattler 停下来
                #
                # 1. 射击队友正在和敌人对射
                # 2. 射击队员正面向敌人基地（为了触发团队协作）
                #
                # 其他更有待补充 ...
                #
                if (shootPlayer.has_status(Status.READY_TO_FIGHT_BACK)
                    or shootPlayer.battler.on_the_same_line_with(oppBase, ignore_brick=True)
                    ):
                    stayID = moveBattler.id
                    stopPlayer = movePlayer

                stopPlayer.set_status(Status.FORCED_STOP_TO_PREVENT_TEAM_HURT)
                returnActions[stayID] = Action.STAY
                stopPlayer.set_current_decision(Action.STAY)
                stopPlayer.set_team_decision(Action.STAY)


        return returnActions

#{ END 'decision/team/prevent_team_hurt.py' }#



#{ BEGIN 'decision/team/cut_through_midline.py' }#

class CutThroughMidlineTeamDecision(TeamDecisionMaker):
    """
    当我方队员与敌人在墙后僵持，并且不得不选择等待的时候
    考虑是否可以打通土墙，因为这个时候也许可以干扰另一路敌人的进攻路线

    """
    def _make_decision(self):

        team = self._team
        map_ = team._map
        base = map_.bases[team.side]
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:

            #
            # 保守起见，先等待一回合
            #
            # TODO:
            #   有可能延误战机！ 5ced7ce1641dd10fdcc776b1
            #   这样才是对的 5ced7d66641dd10fdcc777ae
            #
            # if not player.has_status_in_previous_turns(Status.HAS_ENEMY_BEHIND_BRICK, turns=1):
            #     continue

            with outer_label() as OUTER_CONTINUE:
                action = player.get_current_decision()
                tank = player.tank
                battler = player.battler

                if player.has_team_decision() or player.defeated:
                    continue

                if (Action.is_stay(action)                                # 当前回合处于等待状态
                    and player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)  # 墙后有人造成的
                    and player.has_status(Status.WAIT_FOR_MARCHING)       # 因此等待行军
                    and battler.canShoot # 必须要能够射击
                    and battler.is_near_midline() # 只有中线附近的队友才会触发这个攻击条件
                    ):
                    _oppBattler = player.get_risky_enemy()
                    _oppPlayer = Tank2Player(_oppBattler)
                    # 实际考虑的是它的队员！
                    oppPlayer = _oppPlayer.teammate
                    oppBattler = oppPlayer.battler
                    oppTank = oppBattler.tank

                    if oppPlayer.defeated: # 对方已经输了，就不用管了 ...
                        continue

                    x1, y1 = battler.xy
                    dx = np.sign( base.x - x1 )
                    x2 = x1 + dx
                    y2 = y1
                    shootAction = Action.get_shoot_action(x1, y1, x2, y2)

                    if battler.will_destroy_a_brick_if_shoot(shootAction): # 将会打掉一个砖块
                        field = battler.get_destroyed_fields_if_shoot(shootAction)[0]
                        #
                        # 首先判断这一步射击是否会阻止敌人的移动
                        #
                        enemyAttackingRoute = oppBattler.get_shortest_attacking_route()
                        oppAction = oppBattler.get_next_attacking_action(enemyAttackingRoute)
                        oppRealAction = oppPlayer.try_make_decision(oppAction)
                        if (Action.is_move(oppAction)
                            and Action.is_stay(oppRealAction)
                            and oppPlayer.get_risky_enemy() is battler
                            ): # 敌人下回合打算行军，但是受到我方坦克的影响而停止
                            continue # 那就算了

                        #
                        # 判断是否摧毁了敌人进攻路线上的块
                        #
                        _dx = np.sign( base.x - field.x ) # 首先判断这个块是否和当前坦克处在不同测的地图上
                        if _dx != 0 and _dx != dx: # _dx == 0 表示 x = 4 中线的墙可以打掉
                            if field.xy in enemyAttackingRoute:
                                continue # 不要打掉这个块？


                        #
                        # 防止出现我方坦克打掉一个块，对方可以突然出现在 field 前
                        #
                        for enemyMoveAction in oppBattler.get_all_valid_move_actions():
                            with map_.simulate_multi_actions((battler, shootAction), (oppBattler, enemyMoveAction)):
                                if oppBattler.destroyed: # 好吧，还是要判断一下这种情况的 ...
                                    continue
                                for enemy in oppBattler.get_enemies_around():
                                    if enemy is tank:
                                        raise OUTER_CONTINUE

                        #
                        # 现在说明可以射击
                        #
                        player.set_status(Status.READY_TO_CUT_THROUGH_MIDLINE)
                        returnActions[player.id] = shootAction
                        player.set_team_decision(shootAction)

        return returnActions

#{ END 'decision/team/cut_through_midline.py' }#



#{ BEGIN 'decision/team/cooperative_attack.py' }#

class CooperativeAttackTeamDecision(TeamDecisionMaker):
    """
    团队合作拆家策略
    -----------------

    案例
    ------------
    1.  5ceacbd0811959055e22139d   需要预判 1 步  -> 5cec07f30df42d28e72de8d8
    2.  5ce8db66d2337e01c7ab9fae   需要预判 3 步  -> 5cec1a324742030582fad728
    3.  5cec9157641dd10fdcc5f30d   重叠进攻时能够分开射击了
    4.  5cec9a19641dd10fdcc5ff9f   case 3 的另一种实现，提前找到合作路线
    5.  5cec9c10641dd10fdcc60254   case 2 的另一种实现
    6.  5cec9d01641dd10fdcc6045a   合作与不合作路线相同，但是选择了合作
    7.  5cec9d7f641dd10fdcc60556
    8.  5ceca04d641dd10fdcc60aed   case 2 的另一种实现，但是路线更短，因为将合作触发条件放宽到非严格过中线！
    9.  5ceca0ab641dd10fdcc60bb6   将合作条件放宽到非严格过中线可以触发的合作拆家
    10. 5ceca21b641dd10fdcc60d4d
    11. 5ceca3c3641dd10fdcc61071
    12. 5ceca80d641dd10fdcc617e9
    13. 5cecabbd641dd10fdcc61d34
    14. 5cecfa94641dd10fdcc69661

    触发前提
    --------------
    在双方均到达对方基地的前提下，假定双方坦克不会再发生交火。在这种情况下，可以认为找到的
    最短路线即为实际可走的、不受敌方影响的最短路线。那么可以进行团队合作，寻找一条两人合作下
    距离更加短的进攻路线


    实现方法
    --------------
    下面给出一种简单的实现方法（只预判一回合，更加复杂的情况尚未能实现）

    这个策略中存在主攻队员和辅助队员的角色划分。这个并不能在一开始就得出定论，而是要通过判断。

    首先，合作拆家所希望达到的效果是，辅助队员帮助主攻队员清除其路线上的土墙，从而减短主攻队员的
    攻击路线长度。每清除掉一个土墙，能够减少的路径长度为 2

    因此，首先在 delay = 1 的限制条件下，找到其中一个进攻队员所有可能的最短路线。 delay = 1 是允许的，
    因为一个土墙的权重是 2 ，打掉 delay = 1 的路线上的一个土墙，可以得到比 delay = 0 的最短路线更加短的路线。
    然后考虑另一个进攻队员当前回合所有可能的攻击行为。找到这些攻击行为下能够摧毁掉的 fields ，如果恰好是
    位于另一队员攻击路线上的土墙，那么就找到了一条双人合作下的更短路线。

    依照上述方法，可以列举出所有可能的最短路线。对这些路线长度进行排序以找到最短的路线，即为团队合作下更优
    的一种拆家路线。


    补充的更复杂实现
    -----------------
    有的时候会出现两个队友攻击路线相同且刚好互相不会影响 5ce8db66d2337e01c7ab9fae ，这种情况下实际上仍然
    有机会产生团队合作，但是需要预判 3 步，第一步首先考虑所有可能的进攻行为，第二步按照正常的进攻方向，第三步
    再尝试寻找团队更优路线，如果此时可以找到团队合作路线，那么当前回合就先采用第一步的进攻行为。第二步照常进攻
    到了第三步的时候就会被上面那种单回合的合作拆家决策找到合作路线。


    特判情况
    -----------
    1. 考虑这样一种情况，当前两个队友进攻路线长度相同，两者下一步同时攻击一个块，假如让其中一个坦克停止攻击
    在下回合可以得到更加短的进攻路线，那么就让这个队员暂时停下来。这种情况通常对应着最后拆基地的几步，一个队员
    暂时停下来，让另一个队员拆到前面的墙，然后他下回合马上可以打掉基地，最短路线长度是 2 ，
    如果双方此时是同时开火的，那么最短路线长度是 3

    2. 假设一个队友这回合打掉墙，另一个队友下回合可以到达这个队友身后，下回合前面的队友闪避，后面的队友射击，
    那么最短路线长度是 2 ，如果此时前一个队员等待一回合，后面的队员将无法射击，那么最短路线长度将是 3

    """
    IS_MIDDLE_FIRST = True # 优先中路搜索
    IS_X_AXIS_FIRST = True # 优先 x-轴优先搜索

    def _find_cooperative_solution(self, attackingPlayer, assistantPlayer):
        """
        给定 attackingPlayer 和 assistantPlayer ，尝试寻找一种最短的进攻路线
        如果有个可行的方案，那么只返回找到的第一个

        Return:
            - solution   (attackingPlayer, route, realAction, assistantPlayer, shootAction) / None

        """
        team = self._team
        map_ = team._map
        oppBase = map_.bases[1 - team.side]

        IS_MIDDLE_FIRST = self.__class__.IS_MIDDLE_FIRST
        IS_X_AXIS_FIRST = self.__class__.IS_X_AXIS_FIRST

        attackingBattler = attackingPlayer.battler
        assistantBattler = assistantPlayer.battler

        for route in attackingBattler.get_all_shortest_attacking_routes(delay=1, middle_first=IS_MIDDLE_FIRST, x_axis_first=IS_X_AXIS_FIRST):
            for shootAction in assistantBattler.get_all_valid_shoot_actions():
                destroyedFields = assistantBattler.get_destroyed_fields_if_shoot(shootAction)
                if len(destroyedFields) == 1:
                    field = destroyedFields[0]
                    if isinstance(field, BrickField) and field.xy in route: # 拆到了一个队友进攻路线上的土墙
                        #
                        # 首先考虑打掉的是不是同一个块
                        #
                        # 打掉同一个块的情况下，当且仅当攻击方已经面向对方基地时有效，否则起不到增加长度的效果
                        #
                        attackAction = attackingBattler.get_next_attacking_action(route)
                        if Action.is_shoot(attackAction):
                            destroyedFields2 = attackingBattler.get_destroyed_fields_if_shoot(attackAction)
                            if len(destroyedFields2) == 1 and destroyedFields2[0] is field: # 打掉的是同一个块
                                if not attackingBattler.on_the_same_line_with(oppBase, ignore_brick=True):
                                    continue # 只有当攻击方面对对方基地时，才能起到减少路线长度的效果
                                else: # 否则可以让攻击方这回合等待
                                    realAction = Action.STAY
                                    return (attackingPlayer, route, realAction, assistantPlayer, shootAction)

                        realAction = attackingPlayer.try_make_decision(attackAction)
                        if not Action.is_stay(realAction):
                            return (attackingPlayer, route, realAction, assistantPlayer, shootAction)

        # 找不到，返回 None
        return None


    def _make_decision(self):

        team = self._team
        map_ = team._map
        oppBase = map_.bases[1 - team.side]
        player1, player2 = team.players
        returnActions = [ player.get_current_decision() for player in team.players ]

        if player1.defeated or player2.defeated: # 不是两个人就不需要考虑合作了
            return returnActions
        elif ( not player1.battler.is_in_enemy_site(include_midline=True)
            or not player2.battler.is_in_enemy_site(include_midline=True)
            ): # 两者必须同时在对方基地，并且是严格的不包含中线
               #
               # 条件放宽了，现在允许包含中线 5cec9e9d641dd10fdcc60783
               #
            return returnActions
        elif ( player1.has_status(Status.ENCOUNT_ENEMY)
            or player2.has_status(Status.ENCOUNT_ENEMY)
            or player1.has_status(Status.WAIT_FOR_MARCHING)
            or player2.has_status(Status.WAIT_FOR_MARCHING)
            or player1.has_status(Status.PREVENT_BEING_KILLED)
            or player2.has_status(Status.PREVENT_BEING_KILLED)
            ): # 不可以拥有和敌人遭遇战斗相关的状态
            return returnActions

        IS_MIDDLE_FIRST = self.__class__.IS_MIDDLE_FIRST
        IS_X_AXIS_FIRST = self.__class__.IS_X_AXIS_FIRST

        #
        # 不需要判断是否具有团队信号?
        #
        # 事实上他碰巧提供了一个很好的案例 5cec9157641dd10fdcc5f30d
        # 最后一步的时候由于覆盖了 READY_TO_LEAVE_TEAMMATE 的团队策略，使得最后一步合作得以顺利实现！
        #

        solutions = [] # -> [ (attackingPlayer, route, realAction, assistantPlayer, shootAction) ]

        for attackingPlayer, assistantPlayer in [ (player1, player2), (player2, player1) ]:
            attackingBattler = attackingPlayer.battler
            assistantBattler = assistantPlayer.battler

            if not assistantBattler.canShoot: # 当前回合不能进攻，那就无法发起协助了 ...
                continue

            _route1 = attackingBattler.get_shortest_attacking_route()
            _route2 = assistantBattler.get_shortest_attacking_route()
            minRouteLength = min(_route1.length, _route2.length)
            #
            # 攻击方进攻路线长度比辅助方长 2 步以上，那么直接跳过
            #--------------------------------------------------------
            # 因为单回合决策下至多可以让一个队员的路线长度减 2，如果进攻方比辅助方的攻击路线长 2 步以上，那么
            # 一回合内无论如何都不可能让进攻方的路线长度短于辅助方当前回合的最短路线长度，在这种情况下即使可以
            # 发生合作，也是没有意义的，甚至可能拖延辅助方的进攻节奏（但是并不能排除可以多回合帮助，然而这个情况
            # 非常复杂，所以在此不考虑了）
            #
            if _route1.length - _route2.length >= 2:
                continue

            solution = self._find_cooperative_solution(attackingPlayer, assistantPlayer)
            if solution is not None:
                solutions.append(solution)

            with map_.auto_revert() as counter:
                #
                # 现在往后模拟两回合 5ce8db66d2337e01c7ab9fae
                #
                # 第一步随便攻击，第二步按照正常的攻击方向，第三步看是否有合适的攻击路线
                #
                _cachedActions = set() # 缓存已经尝试过的第一步两个方向
                for route1 in attackingBattler.get_all_shortest_attacking_routes(delay=1, middle_first=IS_MIDDLE_FIRST, x_axis_first=IS_X_AXIS_FIRST): # 攻击方第一步允许 delay = 1
                    action1 = attackingBattler.get_next_attacking_action(route1)
                    realAction1 = attackingPlayer.try_make_decision(action1)
                    if Action.is_stay(realAction1):
                        continue
                    for route2 in assistantBattler.get_all_shortest_attacking_routes(middle_first=IS_MIDDLE_FIRST, x_axis_first=IS_X_AXIS_FIRST):
                        action2 = assistantBattler.get_next_attacking_action(route2)
                        realAction2 = assistantPlayer.try_make_decision(action2)
                        if Action.is_stay(realAction2):
                            continue
                        key = (action1, action2)
                        if key in _cachedActions:
                            continue
                        _cachedActions.add(key)
                        with map_.auto_revert() as counter:
                            ## 模拟两步 ##
                            map_.multi_simulate((attackingBattler, action1), (assistantBattler, action2))
                            counter.increase()
                            # 模拟两步找到路线
                            solution = self._find_cooperative_solution(attackingPlayer, assistantPlayer)
                            if solution is not None:
                                solutions.append( (attackingPlayer, route1, action1, assistantPlayer, action2) )
                                continue
                            ## 模拟三步 ##
                            action11 = attackingBattler.get_next_attacking_action()
                            action22 = assistantBattler.get_next_attacking_action()
                            map_.multi_simulate((attackingBattler, action11), (assistantBattler, action22))
                            counter.increase()
                            # 模拟三步找到路线
                            solution = self._find_cooperative_solution(attackingPlayer, assistantPlayer)
                            if solution is not None:
                                solutions.append( (attackingPlayer, route1, action1, assistantPlayer, action2) )
                                continue

        if len(solutions) > 0:
            solutions.sort(key=lambda tup: tup[1].length)

            for attackingPlayer, route, realAction, assistantPlayer, shootAction in solutions:
                attackingBattler = attackingPlayer.battler
                assistantBattler = assistantPlayer.battler
                returnActions[attackingBattler.id] = realAction
                returnActions[assistantBattler.id] = shootAction
                attackingPlayer.set_current_attacking_route(route)
                attackingPlayer.set_current_decision(realAction)
                attackingPlayer.set_team_decision(realAction)
                assistantPlayer.set_current_decision(shootAction)
                assistantPlayer.set_team_decision(shootAction)
                assistantPlayer.set_status(Status.HELP_TEAMMATE_ATTACK)
                break

        return returnActions

#{ END 'decision/team/cooperative_attack.py' }#



#{ BEGIN 'decision/team/dummy_ending.py' }#

class TeamDecisionDummyEnding(TeamDecisionMaker):
    """
    用于结束 DecisionChain 的结尾

    """
    def is_handled(self, result):
        """
        返回 True ，这样 DecisionChain 就会结束
        """
        return True

    def make_decision(self):
        """
        将 player 缓存的结果直接返回

        """
        team = self._team
        player1, player2 = team.players

        action1 = player1.get_current_decision()
        action2 = player2.get_current_decision()

        return [ action1, action2 ]

#{ END 'decision/team/dummy_ending.py' }#



#{ BEGIN 'player.py' }#

class Player(DecisionMaker):

    # 不能处理的情况，返回 Action.INVALID
    #------------------------------------
    # 值得注意的是，由于 Player 仅仅被 team 判断，signal 仅用于玩家与团队间交流，因此团队在判断时，
    # 不考虑玩家返回的信号，尽管玩家实际返回的值是 (action, signal)
    #
    UNHANDLED_RESULT = Action.INVALID

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
        self._team = None             # Tank2Team
        self._teammate = None         # Tank2Player
        self._opponents = None        # [Tank2Player, Tank2Player]
        self._status = set()          # 当前回合的状态，可以有多个，每回合情况
        self._labels = set()          # 对手给我做的标记，标记后长期有效
        self._riskyEnemy = None       # 缓存引起潜在风险的敌人 BattleTank
        self._currentRoute = None     # 缓存这回合的攻击路线。这个属性加入较早，只缓存了 marching 逻辑下的路线
        self._currentDecision = None  # 缓存决策结果，注：每调用一次 make_decision 就会自动修改一次这个结果
        self._teamDecision = None     # 缓存团队策略


    class _SnapshotManager(object):
        """
        用于管理 player 还原点的创建、选择回滚等行为
        ---------------------------------------------
        可以为 player 在决策过程中产生的临时变量创建快照，如果在此后又进行了重新决策，但是又不想让这个
        决策修改之前决策时留下的临时变量，那么就可以在新的决策前先通过这个类创建一个快照，结束后再通过快照
        进行回滚。


        关于还原点的创建
        ----------------
        1. 对于可能被修改地址指向内存的属性，需要创建一个深拷贝，例如 set, list 类型的属性
        2. 对于只是储存引用的属性，那么此处只需要复制引用。这对于采用单例模式设计的类的实例来说是必须的
        3. 对于不可变对象，只需进行简单的值复制

        """
        MUTABLE_ATTRIBUTES   = ( "_status", "_labels" )
        IMMUTABLE_ATTRIBUTES = ( "_currentDecision", "_teamDecision" )
        REFERENCE_ATTRIBUTES = ( "_currentRoute", "_riskyEnemy" )
        TEMPORARY_ATTRIBUTES = MUTABLE_ATTRIBUTES + IMMUTABLE_ATTRIBUTES + REFERENCE_ATTRIBUTES

        def __init__(self):
            self._snapshot = None
            self._discarded = False # 是否废弃当前快照，让 player 的状态永久改变

        def create_snapshot(self):
            """
            创建一个快照
            由于决策时可能还会更改敌人的状态，所以实际上是给所有人创建快照
            """
            snapshot = self._snapshot = {} # (side, id) -> attributes
            for _key, player in Tank2Player._instances.items():
                cache = snapshot[_key] = {}
                for attr, value in player.__dict__.items():
                    if attr in self.__class__.MUTABLE_ATTRIBUTES:
                        cache[attr] = deepcopy(value) # 创建深拷贝
                    elif attr in self.__class__.IMMUTABLE_ATTRIBUTES:
                        cache[attr] = value # 复制值
                    elif attr in self.__class__.REFERENCE_ATTRIBUTES:
                        cache[attr] = value # 复制引用

        def restore(self):
            """
            恢复到还原点的状态
            """
            if self._discarded: # 保存更改的情况下，不再回滚
                return
            snapshot = self._snapshot
            for _key, player in Tank2Player._instances.items():
                cache = snapshot[_key]
                for attr in self.__class__.TEMPORARY_ATTRIBUTES:
                    player.__dict__[attr] = cache[attr]

        def discard_snapshot(self):
            """
            是否丢弃当前 snapshot，保存变更。
            之后如果再调用 restrore，将不会当前 snapshot 还原 player 的状态
            """
            self._discarded = True


    def __eq__(self, other):
        return self.side == other.side and self.id == other.id

    def __repr__(self):
        return "%s(%d, %d, %d, %d)" % (
                self.__class__.__name__, self.side, self.id,
                self._tank.x, self._tank.y)

    def __copy__(self):
        return self

    def __deepcopy__(self): # singleton !
        return self

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
    def teammate(self): # -> Tank2Player
        return self._teammate

    @property
    def opponents(self): # -> [Tank2Player, Tank2Player]
        return self._opponents

    @contextmanager
    def create_snapshot(self):
        """
        创建一个还原点，然后该 player 进行决策，决策完成后回滚
        """
        try:
            manager = self.__class__._SnapshotManager()
            manager.create_snapshot()

            yield manager # 可以选择不接 snapshot

        except Exception as e:
            raise e
        finally:
            manager.restore()

    def set_team(self, team):
        self._team = team

    def set_teammate(self, player): # -> Tank2Player
        assert isinstance(player, Tank2Player) and player.side == self.side
        self._teammate = player

    def set_opponents(self, opponents): # -> [Tank2Player]
        for player in opponents:
            assert isinstance(player, Tank2Player) and player.side != self.side
        self._opponents = opponents

    def get_risky_enemy(self):
        """
        引起预期行为被拒的敌人，因为该敌人有可能在我方采用预期行为的下一回合将我方击杀
        """
        return self._riskyEnemy # -> BattleTank

    def set_risky_enemy(self, enemy):
        self._riskyEnemy = BattleTank(enemy) # 确保为 BattleTank 对象

    def get_current_decision(self): # 返回最后一次决策的结果，用于队员间交流
        return self._currentDecision

    def set_current_decision(self, action): # 用于团队设置队员的当前决策
        self._currentDecision = action

    def get_team_decision(self): # 获得当前的团队决策
        return self._teamDecision

    def has_team_decision(self):
        return ( self._teamDecision is not None )

    def set_team_decision(self, action): # 用于团队设置队员的团队决策
        self._teamDecision = action

    def get_current_attacking_route(self):
        return self._currentRoute

    def set_current_attacking_route(self, route):
        self._currentRoute = route

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

    def has_status_in_previous_turns(self, status, turns=1):
        return self._team.has_status_in_previous_turns(self, status, turns=turns)

    def has_status_recently(self, status, turns):
        return self._team.has_status_recently(self, status, turns)

    def get_previous_action(self, back=1):
        return self._team.get_previous_action(self, back)

    def get_previous_attacking_route(self):
        return self._team.get_previous_attcking_route(self)

    def _is_safe_action(self, action):
        """
        评估该这个决策是否安全

        Return:
            - issafe   bool   安全
        """
        tank    = self._tank
        map_    = self._map
        battler = self._battler
        teammate = map_.tanks[tank.side][1 - tank.id]

        if not map_.is_valid_action(tank, action): # 先检查是否为有效行为
            return False

        if Action.is_stay(action):
            return True

        # 移动情况下有一种可能的风险
        #--------------------------
        # 1. 需要考虑移动后恰好被对方打中
        # 2. 移动后恰好遇到两个敌人，假设当前回合敌人不动
        # -------------------------
        if Action.is_move(action):
            oppBattlers = [ _player.battler for _player in self._opponents ]
            riskFreeOpps = []
            for oppBattler in oppBattlers:
                if not oppBattler.canShoot: # 对手本回合无法射击，则不必担心
                    riskFreeOpps.append(oppBattler)
            with map_.simulate_one_action(tank, action): # 提交地图模拟情况

                if len( battler.get_enemies_around() ) > 1: # 移动后遇到两个敌人
                    battler1, battler2 = oppBattlers
                    x1, y1 = battler1.xy
                    x2, y2 = battler2.xy
                    if x1 != x2 and y1 != y2: # 并且两个敌人不在同一直线上
                        self.set_risky_enemy(battler1) # 随便设置一个？
                        return False

                for oppBattler in oppBattlers:
                    if oppBattler.destroyed:
                        continue
                    elif oppBattler in riskFreeOpps:
                        continue
                    for enemy in oppBattler.get_enemies_around():
                        if enemy is tank: # 移动后可能会被敌人打中
                            self.set_risky_enemy(oppBattler)
                            return False


        # 射击情况下有两种可能的危险
        #--------------------------
        # 1. 打破一堵墙，然后敌人在后面等着
        #      注意区分两个敌人的情况！ 5ce92ed6d2337e01c7abf544
        # 2. 身边没有闪避的机会，打破一堵墙，对方刚好从旁路闪出来
        # 3. 打到队友！ 5ce90c6dd2337e01c7abce7a
        #---------------------------
        if Action.is_shoot(action):
            destroyedFields = battler.get_destroyed_fields_if_shoot(action)
            if not teammate.destroyed and teammate in destroyedFields:
                return False # 打到队友当然不安全！
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
                    for oppAction in oppBattler.get_all_valid_move_actions(): # 任意移动行为
                        with map_.simulate_one_action(oppBattler, oppAction): # 模拟敌方行为
                            for field in destroyedFields:
                                if field.xy == oppTank.xy:
                                    break # 对方下一步不可能移动到我即将摧毁的 field 上，所以这种情况是安全的
                            else:
                                for enemy in oppBattler.get_enemies_around():
                                    if enemy is tank: # 敌方原地不动或移动一步后，能够看到该坦克
                                        # 还可以尝试回避
                                        actions = battler.try_dodge(oppBattler)
                                        if len(actions) == 0: # 无法回避，危险行为
                                            self.set_risky_enemy(oppBattler)
                                            return False

        return True # 默认安全？


    def try_make_decision(self, action, instead=Action.STAY):
        """
        用这个函数提交决策
        如果这个决策被判定是危险的，那么将提交 instead 行为
        """
        if not Action.is_valid(action):
            return instead
        elif not self._is_safe_action(action):
            return instead
        else:
            return action


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
                            self.set_risky_enemy(_oppBattler)
                            return False # 可能被偷袭

            else: # 此处判断不会被偷袭
                return True
        else:
            return False # 不能移动，当然不安全 ...


    def is_safe_to_break_overlap_by_move(self, action, oppBattler):
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
                        self.set_risky_enemy(_oppBattler)
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

        _route = battler.get_route_to_enemy_by_move(oppBattler)
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

        self._currentDecision = action # 缓存决策
        return ( action, returnSignal )


    def _make_decision(self, signal):

        player  = self
        battler = player.battler

        if player.defeated:
            player.set_status(Status.DIED)
            return self.__class__.UNHANDLED_RESULT

        if not battler.canShoot:
            player.set_status(Status.RELOADING)

        if battler.is_face_to_enemy_base():
            player.set_status(Status.FACING_TO_ENEMY_BASE)

        if (not player.has_label(Label.DONT_WITHDRAW)
            and player.has_label(Label.KEEP_ON_WITHDRAWING)
            and WithdrawalDecision.ALLOW_WITHDRAWAL
            ):
            player.remove_status(Status.AGGRESSIVE, Status.DEFENSIVE, Status.STALEMENT)
            player.set_status(Status.WITHDRAW) # 先保持着 这个状态


        decisions = DecisionChain(

                    LeaveTeammateDecision(player, signal),
                    AttackBaseDecision(player, signal),
                    EncountEnemyDecision(player, signal),
                    OverlappingDecision(player, signal),
                    BaseDefenseDecision(player, signal),
                    BehindBrickDecision(player, signal),
                    FollowEnemyBehindBrickDecision(player, signal),
                    WithdrawalDecision(player, signal),
                    ActiveDefenseDecision(player, signal),
                    MarchingDecision(player, signal),

                )


        res = decisions.make_decision()

        if decisions.is_handled(res):
            return res

        return self.__class__.UNHANDLED_RESULT

#{ END 'player.py' }#



#{ BEGIN 'team.py' }#

class Team(DecisionMaker):

    UNHANDLED_RESULT = [ Action.STAY, Action.STAY ] # 实际上不可能碰到 team 不能决策的情况，否则找谁决策呀 ...

    def __init__(self, *args, **kwargs):
        if __class__ is self.__class__:
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
        self._previousActions = [] # 历史行为

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
                "status": [], # [ set(), set() ] 每轮的状态
                "labels": [ set(), set() ], # [ set(), set() ] 已有的标记
                "previousRoute": [ None, None ]  # [ Route, Route ]
                }
        self._memory = memory
        self._player1.add_labels(*memory["labels"][0])
        self._player2.add_labels(*memory["labels"][1])


    def dump_memory(self):
        memory = self._memory
        memory["status"].append([
                self._player1.get_status(),
                self._player2.get_status(),
                ])
        memory["labels"] = [
                self._player1.get_labels(),
                self._player2.get_labels(),
                ]
        memory["previousRoute"] = [
                self._player1.get_current_attacking_route(),
                self._player2.get_current_attacking_route(),
                ]
        return memory

    def get_memory(self):
        return self._memory

    def set_previous_actions(self, previousActions):
        """
        由 botzone input 获得的过去动作，可以将其视为一种记忆
        """
        self._previousActions = previousActions

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
        for turn in range( len(allStatus) - 1 ,
                           len(allStatus) - 1 - turns,
                           -1 ): # 逆序
            try:
                previousStatus = allStatus[turn][player.id]
            except IndexError: # 可能 allStatus 为空
                return False
            if previousStatus is None:
                return False
            elif status not in previousStatus:
                return False
        else:
            return True

    def has_status_recently(self, player, status, turns):
        """
        最近的几回合内是否曾经拥有过某个状态

        """
        team = player.team
        memory = team.get_memory()
        allStatus = memory["status"]
        if len(allStatus) == 0:
            return False

        for turn in range( len(allStatus) - 1 ,
                           len(allStatus) - 1 - turns,
                           -1 ):
            try:
                previousStatus = allStatus[turn][player.id]
                if status in previousStatus:
                    return True
            except IndexError:
                return False
        else:
            return False

    def get_previous_action(self, player, back=1):
        """
        获得一个玩家的操纵坦克的历史行为

        Input:
            - player   Player       玩家实例，不一定是本队的
            - back     int ( >= 1)  前第几回合的历史记录，例如 back = 1 表示前一回合
        """
        assert back >= 1, "back >= 1 is required"
        return self._previousActions[player.id][-back]

    def get_previous_attcking_route(self, player):
        return self._memory[player.id]


    def _make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """
        team = self

        # 假装先让对方以自己的想法决策
        #-------------------------------
        # 分析对方的行为，可以对下一步的行为作出指导
        #
        for oppPlayer in self._opponentTeam.players:
            oppPlayer.make_decision()


        decisions = DecisionChain(

                    IndividualTeamDecision(team),
                    VitalTeamDecision(team),

                    LeaveTeammateTeamDecision(team),
                    ForcedAttackTeamDecision(team),
                    BreakBrickTeamDecision(team),
                    BackToHelpTeamDecision(team),
                    CutThroughMidlineTeamDecision(team),
                    CooperativeAttackTeamDecision(team),
                    PreventTeamHurtTeamDecision(team),

                    TeamDecisionDummyEnding(team),
                )

        res = decisions._make_decision()

        # for func in [ find_all_routes_for_shoot, find_all_routes_for_move ]:
        #     if not hasattr(func, "__wrapped__"):
        #         continue
        #     _wrapper = func.__wrapped__
        #     if hasattr(_wrapper, "__memory__"):
        #         _memory = _wrapper.__memory__
        #         debug_print(_memory.keys(), len(_memory))
        #         debug_print(sys.getsizeof(_memory))

        return res

    # @override
    def make_decision(self):
        """
        如果有的玩家无法决策，那么就将其行为设为 Action.STAY
        事实上这种情况是不应该出现的，但是为了防止出错，此处对决策结果进行检查

        """
        player1 = self._player1
        player2 = self._player2

        action1, action2 = self._make_decision()

        if not player1.is_handled(action1):
            action1 = Action.STAY
        if not player2.is_handled(action2):
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
        self._pastActions = { # 由 requests, responses 解析而来的历史动作记录
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

        bluePlayer0 = Tank2Player(tanks[BLUE_SIDE][0], map_)
        bluePlayer1 = Tank2Player(tanks[BLUE_SIDE][1], map_)
        redPlayer0  = Tank2Player(tanks[RED_SIDE][0], map_)
        redPlayer1  = Tank2Player(tanks[RED_SIDE][1], map_)
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
        blueTeam.set_previous_actions([
            terminal.get_past_actions(BLUE_SIDE, bluePlayer0.id),
            terminal.get_past_actions(BLUE_SIDE, bluePlayer1.id),
            ])
        redTeam.set_previous_actions([
            terminal.get_past_actions(RED_SIDE, redPlayer0.id),
            terminal.get_past_actions(RED_SIDE, redPlayer1.id),
            ])

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
            allStatus = [ player.get_status().copy() for player in myPlayers ]
            allLabels = [ player.get_labels().copy() for player in myPlayers ]

        if SIMULATOR_ENV:
            oppActions = oppTeam.make_decision()
            oppAllStatus = [ player.get_status().copy() for player in oppPlayers ]
            oppAllLabels = [ player.get_labels().copy() for player in oppPlayers ]

        if SIMULATOR_ENV:
            _CUT_OFF_RULE = "-" * 20
            _SIDE_NAMES = ["Blue", "Red"]

            simulator_print("Decisions for next turn:")
            simulator_print(_CUT_OFF_RULE)

            def _print_decision(actions, side, allStatus, allLabels):
                for id_, action in enumerate(actions):
                    _output = "%-4s %02d: %-11s [status] %s" % (
                            _SIDE_NAMES[side], id_+1, Action.get_name(action),
                            ", ".join( Status.get_name(status) for status in allStatus[id_] ),
                         )
                    if allLabels[id_]:
                        _output += "  [label] %s" % (
                                ", ".join( Label.get_name(label) for label in allLabels[id_] )
                            )
                    simulator_print(_output)

            _print_decision(actions, side, allStatus, allLabels)
            _print_decision(oppActions, 1-side, oppAllStatus, oppAllLabels)

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

            "time": round(t2-t1, 4),
            "storage": sys.getsizeof(DataSerializer.serialize(data))

            }

        terminal.make_output(actions, stream=ostream, debug=debugInfo, data=data)


if __name__ == '__main__':
    main()

#{ END 'main.py' }#



