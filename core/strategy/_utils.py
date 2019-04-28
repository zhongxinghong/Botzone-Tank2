# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:22:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 12:35:33
"""
工具类
"""

__all__ = [

    "get_destroyed_fields",

    "find_shortest_route",

    ]

from ..const import DIRECTIONS_URDL
from ..global_ import np, deque
from ..utils import debug_print
from ..action import Action
from ..field import Field, EmptyField, SteelField, WaterField

#{ BEGIN }#

def get_destroyed_fields(tank, action, map):
    """
    下一回合某坦克执行一个射击行为后，将会摧毁的 fields

    用于单向分析 action 所能造成的影响，不考虑对方下一回合的决策

    - 不判断自身是否与其他 tank 重叠
    - 如果对方是 tank 认为对方下回合不开炮

    Return:
        - fields   [Field]/[]   被摧毁的 fields
                                如果没有对象被摧毁，则返回空列表
    """
    map_ = map
    assert map_.is_valid_shoot_action(tank, action)
    x, y = tank.xy

    _dx = Action.DIRECTION_OF_ACTION_X
    _dy = Action.DIRECTION_OF_ACTION_Y

    action %= 4 # 使之与 dx, dy 的 idx 对应

    while True: # 查找该行/列上是否有可以被摧毁的对象

        x += _dx[action]
        y += _dy[action]

        if not map_.in_map(x, y):
            break

        currentFields = map_[x, y]
        if len(currentFields) == 0: # 没有对象
            continue
        elif len(currentFields) > 1: # 均为坦克
            return currentFields
        else: # len == 1
            field = currentFields[0]
            if isinstance(field, EmptyField): # 空对象
                continue
            elif isinstance(field, WaterField): # 忽视水路
                continue
            elif isinstance(field, SteelField): # 钢墙不可摧毁
                return []
            else:
                return currentFields

    return [] # 没有任何对象被摧毁


def find_shortest_route(start, end, matrix_T, side=-1,
                        cannot_reach_type=[Field.STEEL, Field.WATER]):
    """
    BFS 寻找最短路径

    特点：土墙当成两格

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
    #     "weight": int ( >= 1 )   这个节点的权重
    # ]
    startNode = [ (x1, y1), None, 1 ] # tank 块，权重为 1
    endNode   = [ (x2, y2), None, 1 ] # 找到终点后设置 endNode 的父节点
    tailNode  = [ (-1, -1), endNode, -1 ] # endNode 后的节点

    queue = deque() # deque( [Node] )
    marked = np.zeros_like(matrix, dtype=np.bool8)

    width, height = matrix.shape # width, height 对应着转置前的 宽高

    def _in_matrix(x, y):
        return 0 <= x < width and 0 <= y < height

    def _enqueue_URDL(node):
        for dx, dy in DIRECTIONS_URDL:
            x, y = node[0]
            x3 = x + dx
            y3 = y + dy
            if not _in_matrix(x3, y3) or not matrixCanReach[x3, y3]:
                continue
            weight = 1 # 默认权重
            if matrix[x3, y3] == Field.BRICK: # 墙算作 2 个节点
                weight = 2
            nextNode = [ (x3, y3), node, weight ]
            queue.append(nextNode)


    _enqueue_URDL(startNode)

    while len(queue) > 0:
        node = queue.popleft()

        if node[2] > 1:  # 如果权重大于 1 则减小权重 1 ，直到权重为 1 才算真正到达
            node[2] -= 1
            queue.append(node) # 相当于走到的下一个节点
            continue

        x, y = node[0]

        if marked[x, y]:
            continue
        marked[x, y] = True

        if x == x2 and y == y2:  # 此时 node.xy == endNode.xy
            endNode[1] = node[1]
            break

        _enqueue_URDL(node)


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