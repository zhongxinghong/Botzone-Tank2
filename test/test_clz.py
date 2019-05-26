# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 03:30:54
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-26 08:25:58

from typing import Iterable
from contextlib import contextmanager

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

counter = 0

@contextmanager
def auto_revert():
    try:
        yield
        global counter
        counter = 0
        print("counter revert to %s" % counter)
    except Exception as e:
        raise e

@contextmanager
def inner_context():
    try:
        yield
        print("inner_context")
    except Exception as e:
        raise e

def rollback():
    with auto_revert():
        with auto_revert():
            for _ in range(5):
                global counter
                counter += 1
                print("current counter: %s" % counter)
                with auto_revert():
                    with inner_context():
                        if counter == 2:
                            return

#rollback()


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

'''
route = Route([ (1,2), (3,4), (4,5) ])

print(isinstance(route, Iterable))

it = iter(route)

print(it)

for node in route:
    print(node)
    '''


class Singleton(type):
    """
    Singleton Metaclass
    @link https://github.com/jhao104/proxy_pool/blob/428359c8dada998481f038dbdc8d3923e5850c0e/Util/utilClass.py
    """
    _inst = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._inst:
            cls._inst[cls] = super(Singleton, cls).__call__(*args)
        return cls._inst[cls]


class A(object, metaclass=Singleton):

    def __init__(self):
        print("A.__init__")


a = A()
b = A()
c = A()
d = A()
print(a is b)
print(b is c)
print(c is d)



class First(object):

    def get_second(self):
        b = None
        if isinstance(b, Second):
            pass
        return Second()


class Second(object):

    def get_first(self):
        a = None
        if isinstance(a, First):
            pass
        return First()


a = First()
b = Second()
c = a.get_second()
d = b.get_first()
print("ok")


@contextmanager
def aa():
    try:
        yield
    except Exception as e:
        print(e)
        raise e
    finally:
        print("ok")


def fn():

    with aa():
        return True

a = [1,2,3,4]

a.sort(key=lambda item: fn(), reverse=True)

print(a)