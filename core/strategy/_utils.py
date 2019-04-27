# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:22:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 16:35:09
"""
工具类
"""

__all__ = [

    "_find_shortest_route",

    ]

from ..const import DIRECTIONS_UDLR
from ..global_ import np, deque
from ..field import Field

#{ BEGIN }#

def _find_shortest_route(start, end, matrix_T, side=-1,
                         cannot_reach_type=[Field.STEEL, Field.WATER]):
    """
    BFS 寻找最短路径

    Input:
        - start     (int, int)           起始坐标 (x1, y2)
        - end       (int, int)           终点坐标 (x2, y2)
        - matrix_T  np.array( [[int]] )  游戏地图的类型矩阵的转置
        - side      int                  游戏方，默认为 -1，该值会影响对 base 是否可到达的判断
                                         如果为本方基地，则不可到达，如果为对方基地，则可以到达

        - cannot_reach_type   [int]      除了基地以外，其他不可以到达的 field 类型

    Return:
        - route   [(int, int)]  包含 start 和 end 的从 start -> end
                                的最短路径，坐标形式 (x, y)
    """
    matrix = matrix_T
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
    marked = np.zeros_like(matrix, dtype=np.bool8)

    width, height = matrix.shape # width, height 对应着转置前的 宽高

    def _in_matrix(x, y):
        return 0 <= x < width and 0 <= y < height

    def _enqueue_UDLR(node):
        for dx, dy in DIRECTIONS_UDLR:
            x, y = node[0]
            x3 = x + dx
            y3 = y + dy
            if not _in_matrix(x3, y3) or not matrixCanReach[x3, y3]:
                continue
            nextNode = [ (x3, y3), node ]
            queue.append(nextNode)


    _enqueue_UDLR(startNode)

    while len(queue) > 1:
        node = queue.popleft()
        x, y = node[0]

        if marked[x, y]:
            continue
        marked[x, y] = True

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

#{ END }#