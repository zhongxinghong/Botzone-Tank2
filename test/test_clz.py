# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 03:30:54
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 05:08:11

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


for _ in range(3):
    a = Tank("Blue 1")
    b = Tank("Red 1")
    c = Tank("Blue 1")
    d = Tank("Red 1")


print(a)
print(b)
print(c)
print(d)

