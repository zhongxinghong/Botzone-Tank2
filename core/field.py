# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:17:45
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 07:12:02

__all__ = [

    "Field",

    "EmptyField",
    "BaseField",
    "BrickField",
    "SteelField",
    "WaterField",
    "TankField",

    ]

from .action import Action

#{ BEGIN }#

class Field(object):

    DUMMY = -1
    EMPTY = 0
    BASE  = 1
    BRICK = 2
    STEEL = 3
    WATER = 4
    TANK  = 5

    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.destroyed = False

    @property
    def coordinate(self):
        return (self.x, self.y)


class EmptyField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.EMPTY)


class BaseField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.BASE)


class BrickField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.BRICK)


class SteelField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.STEEL)


class WaterField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.WATER)


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