# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-29 22:22:52
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 00:20:53
"""
BFS 搜索最短路径的工具库

"""

__all__ = [

    "find_all_routes_for_move",
    "find_all_routes_for_shoot",
    "find_shortest_route_for_move",
    "find_shortest_route_for_shoot",

    "get_searching_directions",

    "DIRECTIONS_URDL", "DIRECTIONS_ULDR", "DIRECTIONS_DRUL", "DIRECTIONS_DLUR",
    "DIRECTIONS_RULD", "DIRECTIONS_LURD", "DIRECTIONS_RDLU", "DIRECTIONS_LDRU",

    "DEFAULT_BLOCK_TYPES",
    "DEFAULT_DESTROYABLE_TYPES"

    ]

from ..const import DEBUG_MODE, MAP_WIDTH, MAP_HEIGHT
from ..global_ import np, deque
from ..utils import memorize, debug_print, debug_pprint
from ..field import Field, BASE_FIELD_TYPES, TANK_FIELD_TYPES
from .route import Route, INFINITY_ROUTE_LENGTH, INFINITY_WEIGHT, DUMMY_ACTION,\
                    NONE_ACTION, MOVE_ACTION, SHOOT_ACTION, NONE_POINT

#{ BEGIN }#

# y-axis first / vertical first / aggressive
DIRECTIONS_URDL = ( (0, -1), ( 1, 0), (0,  1), (-1, 0) ) # 上右下左
DIRECTIONS_ULDR = ( (0, -1), (-1, 0), (0,  1), ( 1, 0) ) # 上左下右
DIRECTIONS_DRUL = ( (0,  1), ( 1, 0), (0, -1), (-1, 0) ) # 下右上左
DIRECTIONS_DLUR = ( (0,  1), (-1, 0), (0, -1), ( 1, 0) ) # 下左上右

# x-axis first / horizontal first / defensive
DIRECTIONS_RULD = ( ( 1, 0), (0, -1), (-1, 0), (0,  1) ) # 右上左下
DIRECTIONS_LURD = ( (-1, 0), (0, -1), ( 1, 0), (0,  1) ) # 左上右下
DIRECTIONS_RDLU = ( ( 1, 0), (0,  1), (-1, 0), (0, -1) ) # 右下左上
DIRECTIONS_LDRU = ( (-1, 0), (0,  1), ( 1, 0), (0, -1) ) #　左下右上

DEFAULT_BLOCK_TYPES       = ( Field.STEEL, Field.WATER, )
DEFAULT_DESTROYABLE_TYPES = ( Field.BRICK, )
#------------------------
# 通常需要额外考虑的类型有
#
# 1. 两方基地
# 2. 己方坦克和对方坦克
#------------------------


def get_searching_directions(x1, y1, x2=None, y2=None, x_axis_first=False,
                             middle_first=False):
    """
    获得从 (x1, y1) -> (x2, y2) 最优的搜索方向顺序

    Input:
        - (x1, y1)   起点坐标
        - (x2, y2)   终点坐标，可以没有，那么将通过 (x1, y1) 在地图中的相对位置，
                     对应着左上、左下、右上、右下四个区域，确定最佳的搜索顺序

        - x_axis_first   bool   是否采用 x 轴方向优先的搜索方式。默认以垂直方向优先，
                                也就是如果存在到达目标坐标的两条长度相同的路径，
                                会优先从 y 轴方向移动过去，即先上下移动，后左右移动。
                                若选择以水平方向优先，则先左右移动，后上下移动。

                                优先上下移动通常用于侵略，优先左右移动通常用于防御

        - middle_first   bool   是否采用中路优先的搜索方式。默认不采用，而是优先从边路
                                搜索，如果边路和中路有距离相等的路径，那么优先从边路
                                走，如果中路发生冲突，就可以减小被敌人牵制的概率

        注： x 轴优先仅仅在中路优先的成立下才有意义，如果是旁路搜索，则对 x 轴优先的
            设置是无效的

    """
    if x2 is None or y2 is None: # 如果 x2, y2 为空，则默认以地图中点作为目标
        x2 = MAP_WIDTH  // 2
        y2 = MAP_HEIGHT // 2

    if   ( x2 - x1 >= 0 ) and ( y2 - y1 >= 0 ):
        if middle_first:
            return DIRECTIONS_DRUL if not x_axis_first else DIRECTIONS_RDLU
        else:
            return DIRECTIONS_LDRU
    elif ( x2 - x1 >= 0 ) and ( y2 - y1 <= 0 ):
        if middle_first:
            return DIRECTIONS_URDL if not x_axis_first else DIRECTIONS_RULD
        else:
            return DIRECTIONS_LURD
    elif ( x2 - x1 <= 0 ) and ( y2 - y1 >= 0 ):
        if middle_first:
            return DIRECTIONS_DLUR if not x_axis_first else DIRECTIONS_LDRU
        else:
            return DIRECTIONS_RDLU
    elif ( x2 - x1 <= 0 ) and ( y2 - y1 <= 0 ):
        if middle_first:
            return DIRECTIONS_ULDR if not x_axis_first else DIRECTIONS_LURD
        else:
            return DIRECTIONS_RULD

    raise Exception


def _BFS_search_all_routes_for_move(start, end, map_matrix_T, weight_matrix_T,
                                    block_types=DEFAULT_BLOCK_TYPES, x_axis_first=False,
                                    middle_first=False):
    """
    BFS 搜索从 start -> end 的所有路径路径，由短到长依次返回
    ----------------------------------------------------------------------------

    Input:

        - start         (int, int)      起始坐标 (x1, y2)

        - end           (int, int)      终点坐标 (x2, y2) ，其对应的 field 类型必须不在
                                        block_types 的定义里，否则查找到的路径为空

        - map_matrix_T      np.array( [[int]] )   field 类型值的矩阵的转置，坐标形式 (x, y)

        - weight_matrix_T   np.array( [[int]] )   每个格子对应节点的权重，形状与坐标形式同上

        - block_types       [int]       不能够移动到的 field 类型
                                        WARNING:
                                            需要自行指定不能够到达的基地、坦克的类型

        - x_axis_first      bool        是否优先搜索 x 轴方向

        - middle_first      bool        是否采用中路优先的搜索

    Yield From:

        - routes            [Route]     所有可以到达的路径。如果没有搜索到可以到达的路径，则返回空路径

    ----------------------------------------------------------------------------

    def struct Node: // 定义节点模型
    [
        "xy":     (int, int)          目标节点
        "parent": Node/None           父节点
        "step":   int ( >= 0 )        还差几步到达，为 0 表示到达，初始值为 weight - 1
        "weight": const int ( >= 1 )  权重，即搜索时需要在其上耗费的步数
        "last_action": const int      通过什么操作到达这个节点，该情况为移动
    ]

    """
    x1, y1 = start
    x2, y2 = end

    width, height = map_matrix_T.shape # width, height 对应着转置前的 宽高

    matrixMap = map_matrix_T
    matrixWeight = weight_matrix_T

    matrixCanMoveTo = np.ones_like(matrixMap, dtype=np.bool8)
    for _type in block_types:
        matrixCanMoveTo &= (matrixMap != _type)

    # debug_print("map:\n", matrixMap.T)
    # debug_print("weight:\n", matrixWeight.T)
    # debug_print("can move on:\n", matrixCanMoveTo.astype(np.int8).T)

    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION,
        ]

    queue = deque() # queue( [Node] )
    matrixMarked = np.zeros_like(matrixMap, dtype=np.bool8)

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init

    _foundRoute = False

    while len(queue) > 0:

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if (x, y) == end: # 到达终点
            _foundRoute = True
            yield Route(node)
            continue

        if matrixMarked[x, y]:
            continue
        matrixMarked[x, y] = True

        if DEBUG_MODE:
            matrixDistance[x, y] = _get_route_length_by_node_chain(node)

        for dx, dy in get_searching_directions(x1, x2, y1, y2,
                                               x_axis_first=x_axis_first,
                                               middle_first=middle_first):
            x, y = node[0]
            x3 = x + dx
            y3 = y + dy
            if (not (0 <= x3 < width and 0 <= y3 < height) # not in map
                or not matrixCanMoveTo[x3, y3]
                ):
                continue
            weight = matrixWeight[x3, y3]
            queue.append([
                (x3, y3),
                node,
                weight-1,
                weight,
                MOVE_ACTION,
                ])
    '''
    if DEBUG_MODE:
        debug_print("distance matrix:\n", matrixDistance.T)
    '''

    if not _foundRoute:
        yield Route() # 空节点


def _BFS_search_all_routes_for_shoot(start, end, map_matrix_T, move_weight_matrix_T,
                                     shoot_weight_matrix_T, block_types=DEFAULT_BLOCK_TYPES,
                                     destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                                     x_axis_first=False, middle_first=False):
    """
    BFS 搜索从 start 开始到击中 end 的所有路径，由短到长依次返回
    ----------------------------------------------------------------------------

    实现思路：

    通过射击的方式能够比单纯通过移动的方式更快地接近目标，这是显而易见的，毕竟炮弹可以飞行。
    于是，将地图划分为两个区域，一个是可以发动射击的区域，它们仅仅与目标处在同一行或同一列的位置上
    另一个就是常规的移动可达的区域。搜索过程中对着两种情况下相应的节点权重做区分对待即可。

    ---------------------------------------------------------------------------

    Input:

        - start         (int, int)      起始坐标 (x1, y2)

        - end           (int, int)      终点坐标 (x2, y2) ，其对应的 field 类型必须不在
                                        destroyable_types 的定义里，否则查找到的路径为空

        - map_matrix_T            np.array( [[int]] )   field 类型值的矩阵的转置，坐标形式 (x, y)

        - move_weight_matrix_T    np.array( [[int]] )   移动到这个格子所需的步数

        - shoot_weight_matrix_T   np.array( [[int]] )   炮弹到达这个格子所需的步数

        - block_types           [int]   不能够移动到的 field 类型
                                        WARNING:
                                            需要自行指定不能被攻击的基地、坦克的类型

        - destroyable_types     [int]   能够通过射击行为摧毁的 field 类型，未指定在这个变量里的
                                        所有其他 field 类型均默认视为不可摧毁，在以射击的方式进行
                                        搜索时，遇到这样的 field 会跳过
                                        WARNING:
                                            需要自行制定可以被摧毁的基地、坦克的类型

        - x_axis_first          bool    是否优先搜索 x 轴方向

        - middle_first          bool    是否采用中路优先的搜索

    Yield From:

        - routes            [Route]     所有可以到达的路径。如果没有搜索到可以到达的路径，则返回空路径

    --------------------------------------------------------------------------

    def struct Node: // 定义节点模型
    [
        "xy":     (int, int)          目标节点
        "parent": Node/None           父节点
        "step":   int ( >= 0 )        还差几步到达，为 0 表示到达，初始值为 weight - 1
        "weight": const int ( >= 1 )  权重，即搜索时需要在其上耗费的步数
        "last_action": const int      通过什么操作到达这个节点，射击或移动
    ]

    """
    x1, y1 = start
    x2, y2 = end

    width, height = map_matrix_T.shape
    matrixMap = map_matrix_T
    matrixMoveWeight = move_weight_matrix_T
    matrixShootWeight = shoot_weight_matrix_T

    # 哪些位置可以移动到
    matrixCanMoveTo = np.ones_like(matrixMap, dtype=np.bool8)
    for _type in block_types:
        matrixCanMoveTo &= (matrixMap != _type)

    # 那些位置上的 field 可以被摧毁
    matrixCanBeDestroyed = np.zeros_like(matrixMap, dtype=np.bool8)
    for _type in destroyable_types:
        matrixCanBeDestroyed |= (matrixMap == _type)

    # 哪些位置可以对目标发动射击，即 end 向四个方向伸展开的区域
    matrixCanShoot = np.zeros_like(matrixMap, dtype=np.bool8)
    matrixCanShoot[x2, y2] = True
    for dx, dy in get_searching_directions(x1, y1, x2, y2,
                                           x_axis_first=x_axis_first,
                                           middle_first=middle_first):
        x, y = end
        while True:
            x += dx
            y += dy
            if not (0 <= x < width and 0 <= y < height):
                break
            elif matrixMap[x, y] == Field.EMPTY: # 空对象
                pass
            elif matrixMap[x, y] == Field.WATER:
                continue # 水路不可以发动射击，但是可以射过去
            elif not matrixCanBeDestroyed[x, y] and (x, y) != start:
                break # 打一个补丁，不管怎么样，攻击者原地是可以发动射击的 ...
            matrixCanShoot[x, y] = True
            if (x, y) == start: # 已经找到了 start 没有必要再继续找下去了
                break

    # debug_print("map:\n", matrixMap.T)
    # debug_print("weight of move:\n", matrixMoveWeight.T)
    # debug_print("weight of shoot:\n", matrixShootWeight.T)
    # debug_print("can move to:\n", matrixCanMoveTo.astype(np.int8).T)
    # debug_print("can shoot:\n", matrixCanShoot.astype(np.int8).T)
    # debug_print("can be destroyed:\n", matrixCanBeDestroyed.astype(np.int8).T)


    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION, # 对于 start == end 的情况，将返回 startNode，相当于原地等待
        ]

    queue = deque() # queue( [Node] )
    matrixMarked  = np.zeros_like(matrixMap, dtype=np.bool8) # 标记移动到的位置

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init

    _foundRoute = False

    while len(queue) > 0:

        # if start == (8, 1):
        #     debug_print(start)
        #     debug_print([n[0] for n in queue])

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if (x, y) == end:
            _foundRoute = True
            yield Route(node)
            continue

        # 1. 如果当前处在射击区域
        # 2. 或者上回合射击（事实上射击行为必定是可延续的，也就是上回合 canShoot 这回合
        # 必定应该继续 canShoot ，但是对于 WaterField 来说，不属于可以发动射击的区域
        # 因此，如果上回合射进 WaterField 那么上一个判定条件就会失效。但在这种情况下
        # 应该视为射击行为延续，因此需要第二个判定条件）
        #
        if matrixCanShoot[x, y] or node[4] == SHOOT_ACTION:

            # 因为在射击区域中，行为的方向都是单向的，不会出现从射击区域进入移动区域，
            # 或者从射击的下一步移动回到上一步的情况，
            # 因此没有必要对射击行为已到达过的节点位置进行检查和标记

            if DEBUG_MODE:
                matrixDistance[x, y] = _get_route_length_by_node_chain(node)

            # 确定射击方向
            dx = np.sign(x2 - x)
            dy = np.sign(y2 - y)
            x3 = x + dx
            y3 = y + dy

            weight = matrixShootWeight[x3, y3]

            nextNode = [  # 必定可以保证下一个节点仍然处在射击区域，不会到达地图外，
                (x3, y3), # 并且下次还会继续进入这个分支，除非已经到达基地
                node,
                weight-1, # 补偿
                weight,
                SHOOT_ACTION, # 标志着上一步处在射击区域内
                ]

            if weight == 0: # 射击的过渡动作，下一个动作和当前动作同时发生
                queue.appendleft(nextNode) # 添加到开头，下回合马上继续
            else:
                queue.append(nextNode)

        else: # 否则为非射击区域，属于常规移动区域

            if matrixMarked[x, y]: # 只对移动区域进行标记
                continue
            matrixMarked[x, y] = True

            if DEBUG_MODE:
                matrixDistance[x, y] = _get_route_length_by_node_chain(node)

            for dx, dy in get_searching_directions(x1, y1, x2, y2,
                                                   x_axis_first=x_axis_first,
                                                   middle_first=middle_first):
                x3 = x + dx
                y3 = y + dy

                if (not (0 <= x3 < width and 0 <= y3 < height) # not in map
                    or not matrixCanMoveTo[x3, y3]
                    ):
                    continue

                weight = matrixMoveWeight[x3, y3]
                if weight == INFINITY_WEIGHT:
                    continue

                queue.append([
                    (x3, y3),
                    node,
                    weight-1,
                    weight,
                    MOVE_ACTION, # 标志着上一步处在非射击区域内
                    ])

    if not _foundRoute:
        yield Route() # 空节点


@memorize
def find_all_routes_for_move(start, end, matrix_T,
                             block_types=DEFAULT_BLOCK_TYPES,
                             x_axis_first=False, middle_first=False):
    """
    搜索移动到目标的所有路径

    Input:
        - matrix_T   np.array( [[int]] )   游戏地图的类型矩阵的转置

    Yield From:
        - route      Route
    """
    matrixMap = matrix_T

    matrixWeight = np.ones_like(matrixMap)
    matrixWeight[matrixMap == Field.BRICK] = 1 + 1 # 射击一回合，移动一回合
    matrixWeight[matrixMap == Field.STEEL] = INFINITY_WEIGHT
    matrixWeight[matrixMap == Field.WATER] = INFINITY_WEIGHT

    routes = _BFS_search_all_routes_for_move(
                    start, end, matrixMap, matrixWeight, block_types=block_types,
                    x_axis_first=x_axis_first, middle_first=middle_first)

    yield from routes


@memorize
def find_all_routes_for_shoot(start, end, matrix_T,
                              block_types=DEFAULT_BLOCK_TYPES,
                              destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                              x_axis_first=False,
                              middle_first=False):
    """
    搜索移动并射击掉目标的所有路径

    输入输出同上
    """
    matrixMap = matrix_T

    matrixMoveWeight = np.ones_like(matrixMap)   # weight 默认为 1，即移动一回合
    matrixMoveWeight[matrixMap == Field.BRICK]   = 1 + 1  # 射击一回合，移动一回合
    matrixMoveWeight[matrixMap == Field.STEEL]   = INFINITY_WEIGHT
    matrixMoveWeight[matrixMap == Field.WATER]   = INFINITY_WEIGHT

    matrixShootWeight = np.zeros_like(matrixMap) # weight 默认为 0 ，即炮弹可以飞过
    matrixShootWeight[matrixMap == Field.BRICK]  = 1 + 1  # 射击一回合，冷却一回合
    matrixShootWeight[matrixMap == Field.STEEL]  = INFINITY_WEIGHT
    for _type in BASE_FIELD_TYPES:
        matrixShootWeight[matrixMap == _type]    = 1      # 射击一回合，之后就赢了
    for _type in TANK_FIELD_TYPES:
        matrixShootWeight[matrixMap == _type]    = 1 + 1  # 射击一回合，冷却一回合
    # WARNING:
    #   这里只是从理论上分析 TANK, BASE 被打掉对应的权重，实际上我们不希望基地和队友
    #   被打掉，因此在实际使用时，仅仅在 destroyable_types 中添加敌方的坦克即可

    routes = _BFS_search_all_routes_for_shoot(
                    start, end, matrixMap, matrixMoveWeight, matrixShootWeight,
                    block_types=block_types, destroyable_types=destroyable_types,
                    x_axis_first=x_axis_first, middle_first=middle_first)

    yield from routes


def find_shortest_route_for_move(*args, **kwargs):
    """
    搜索移动到目标的最短路径
    """
    for route in find_all_routes_for_move(*args, **kwargs):
        return route # 直接返回第一个 route


def find_shortest_route_for_shoot(*args, **kwargs):
    """
    搜索移动并射击掉目标的最短路径
    """
    for route in find_all_routes_for_shoot(*args, **kwargs):
        return route # 直接返回第一个 route


def _get_route_length_by_node_chain(node):
    """
    [DEBUG] 传入 node chain head ，计算其所代表的节点链对应的距离

    Return:
        - length   int   路线长度，如果是空路线，返回 无穷大长度

    """
    assert isinstance(node, list) and len(node) == 5

    dummyHead = [
        NONE_POINT,
        node,
        -1,
        -1,
        DUMMY_ACTION,
        ]

    route = []
    node = dummyHead
    while True:
        node = node[1]
        if node is not None:
            x, y   = node[0]
            weight = node[3]
            route.append( (x, y, weight) )
        else:
            break

    if len(route) == 0:
        return INFINITY_ROUTE_LENGTH

    return np.sum( r[2] for r in route )


#{ END }#