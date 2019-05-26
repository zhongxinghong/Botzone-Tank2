# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-08 23:18:15
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-26 03:09:54

__all__ = [

    "RouteNode",
    "Route",

    "INFINITY_WEIGHT",
    "INFINITY_ROUTE_LENGTH",

    "DUMMY_ACTION",
    "NONE_ACTION",
    "MOVE_ACTION",
    "SHOOT_ACTION",

    ]

from ..global_ import np, deepcopy
from ..utils import CachedProperty
from ..field import BaseField, BrickField, TankField

#{ BEGIN }#


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

#{ END }#