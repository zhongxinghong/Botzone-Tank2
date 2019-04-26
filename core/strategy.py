# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 07:29:15
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 04:55:20

__all__ = [

    "MoveToWaterStrategy",

    ]

#{ BEGIN }#
import numpy as np
from collections import deque
#{ END }#
from .field import Field
from .action import Action
from .const import DIRECTIONS_UDLR, DEBUG_MODE


#{ BEGIN }#

def _create_map_marked_matrix(map, fill=False, T=True):
    """
    创建地图的标记矩阵

    Input:
        - map    Tank2Map    游戏地图
        - fill   object      初始填充值
        - T      bool        是否转置
    """
    width, height = map.size
    if T:
        width, height = height, width
    return [ [ fill for x in range(width) ] for y in range(height) ]

def _find_nearest_route(start, end, map, side=-1,
                        cannot_reach_type=[Field.STEEL, Field.WATER]):
    """
    寻找最短路径

    Input:
        - start   (int, int)    起始坐标 (x1, y2)
        - end     (int, int)    终点坐标 (x2, y2)
        - map     Tank2Map      游戏地图
        - side    int           游戏方，默认为 -1，该值会影响对 base 是否可到达的判断
                                如果为本方基地，则不可到达，如果为对方基地，则可以到达

        - cannot_reach_type   [int]   除了基地以外，其他不可以到达的 field 类型

    Return:
        - route   [(int, int)]  包含 start 和 end 的从 start -> end
                                的最短路径，坐标形式 (x, y)
    """
    map_   = map
    matrix = map_.matrix_T
    x1, y1 = start
    x2, y2 = end

    matrixCanReach = (matrix != Field.BASE + 1 + side) # BASE, 遵守 Field 中常数的定义规则
    for t in cannot_reach_type:
        matrixCanReach &= (matrix != t)

    # struct Node:
    # [
    #     "xy":     (int, int)     目标节点
    #     "parent": Node or None   父节点
    # ]
    startNode = [ (x1, y1), None ]
    endNode   = [ (x2, y2), None ]    # 找到终点后设置 endNode 的父节点
    tailNode  = [ (-1, -1), endNode ] # endNode 后的节点


    queue = deque() # deque( [Node] )
    marked = _create_map_marked_matrix(map_, fill=False, T=True)

    def _enqueue_UDLR(node):
        for dx, dy in DIRECTIONS_UDLR:
            x, y = node[0]
            x3 = x + dx
            y3 = y + dy
            if not map_.in_map(x3, y3) or not matrixCanReach[x3, y3]:
                continue
            nextNode = [ (x3, y3), node ]
            queue.append(nextNode)


    _enqueue_UDLR(startNode)

    while len(queue) > 1:
        node = queue.popleft()
        x, y = node[0]

        if marked[x][y]:
            continue
        marked[x][y] = True

        if x == x2 and y == y2:  # 此时 node.xy == endNode.xy
            endNode[1] = node[1]
            break

        _enqueue_UDLR(node)


    route = []

    node = tailNode
    while True:
        node = node[1]
        if node is not None:
            route.append(node[0])
        else:
            break

    route.reverse()
    return route


class Strategy(object):
    """
    策略类 抽象基类

    """
    def __init__(self, tank, map, **kwargs):
        """
        Input:
            - tank   TankField   需要做出决策的 tank
            - map    Tank2Map    当前地图
        """
        self._tank = tank
        self._map = map

    def make_decision(self):
        """
        做出决策

        Return:
            - action   int   Action 类中定义的动作编号
        """
        raise NotImplementedError


class MoveToWaterStrategy(Strategy):
    """
    [TEST] 移动向距离自己最近的水域
    """

    def __init__(self, tank, map, water_points=None):
        """
        可以传入 water_points 的坐标
        """
        super().__init__(tank, map)
        self._waterPoints = water_points

    @staticmethod
    def find_water_points(map):
        return np.argwhere(map.matrix_T == Field.WATER) # 转置为 xy 矩阵

    def make_decision(self):
        if self._waterPoints is None:
            self._waterPoints = self.find_water_points(self._map)

        waterPoints = self._waterPoints
        xy = np.array( self._tank.xy )

        _idx = np.square( xy - waterPoints ).sum(axis=1).argmin()
        x2, y2 = nearestWaterPoint = waterPoints[_idx]

        route = _find_nearest_route(
                    self._tank.xy,
                    nearestWaterPoint,
                    self._map,
                    cannot_reach_type=[Field.STEEL] ) # 水域允许到达

        if DEBUG_MODE:
            from pprint import pprint
            self._map.print_out()
            pprint(self._map.matrix)
            print("")
            pprint(route)

        x1, y1 = self._tank.xy
        if len(route) == 0:
            raise Exception("can't reach (%s, %s)" % (x2, y2) )

        if len(route) == 1: # 说明 start 和 end 相同
            x3, y3 = nextPoint = route[0] # 返回 start/end
        else:
            x3, y3 = nextPoint = route[1] # 跳过 start

        return Action.get_action(x1, y1, x3, y3)

#{ END }#