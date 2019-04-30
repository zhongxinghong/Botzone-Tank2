# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:17:45
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 15:47:55
"""
地图区域类
"""

__all__ = [

    "Field",

    "EmptyField",
    "BrickField",
    "SteelField",
    "WaterField",
    "BaseField",
    "TankField",

    "BASE_FIELD_TYPES",
    "TANK_FIELD_TYPES",

    ]

from .action import Action

#{ BEGIN }#

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



#{ END }#