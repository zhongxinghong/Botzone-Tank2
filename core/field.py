# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:17:45
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 02:38:58

__all__ = [

    "Field",

    "EmptyField",
    "BrickField",
    "SteelField",
    "WaterField",
    "BaseField",
    "TankField",

    ]

from .action import Action

#{ BEGIN }#

class Field(object):


    DUMMY     = -1
    EMPTY     = 0
    BRICK     = 1
    STEEL     = 2
    WATER     = 3

    ## rule: BASE + 1 + side
    BASE      = 4 # side = -1
    BLUE_BASE = 5 # side = 0
    RED_BASE  = 6 # side = 1

    ## rule: TANK + 1 + side
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

#{ END }#