# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 03:30:54
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-09 01:06:39

from typing import Iterable

class Tank(object):

    __instances = {}

    def __init__(self, tank):
        print("Create %s" % tank)

    def __new__(cls, tank, *args, **kwargs):
        inst = __class__.__instances.get(tank)
        if inst is None:
            __class__.__instances[tank] = inst = super(Tank, cls).__new__(cls, *args, **kwargs)
            inst._tank = tank
            inst.__inner = tank*2
            print("Create new inst")
        else:
            print("Get old inst")
        return inst

    def __repr__(self):
        return "Tank: %s, inner: %s" % (self._tank, self.__inner)


class UniqueIntEnumMeta(type):

    def __new__(cls, name, bases, attrs):
        offset = attrs.get("__offset__", 0)
        for k, v in attrs.items():
            if isinstance(v, int):
                attrs[k] += offset
        return super(UniqueIntEnumMeta, cls).__new__(cls, name, bases, attrs)


class Signal(object, metaclass=UniqueIntEnumMeta):

    __offset__ = 100

    A = 0
    B = 1

    C = ( A, B )

    @property
    @staticmethod
    def C():
        return (A, B)

    def _test_method(self):
        pass

    @staticmethod
    def _test_static_method():
        pass

    @classmethod
    def _test_class_method():
        pass

    @property
    def _test_property(self):
        return -1


class Route(object):

    def __init__(self, items):
        self._items = items

    def __iter__(self):
        #for xy in self._items:
        #    yield xy
        yield from self._items

'''
for _ in range(3):
    a = Tank("Blue 1")
    b = Tank("Red 1")
    c = Tank("Blue 1")
    d = Tank("Red 1")


print(a)
print(b)
print(c)
print(d)

'''

#print(Signal.A)
#print(Signal.B)
#print(Signal.C) # 未变 ！


route = Route([ (1,2), (3,4), (4,5) ])

print(isinstance(route, Iterable))

it = iter(route)

print(it)

for node in route:
    print(node)