# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-29 22:22:52
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-04 14:30:39
"""
BFS 搜索最短路径的工具库


WARNING:

1. 一定要使用 get_route_length 来求得路线长度，而不是 len(route)
2. 一定要记得 get_route_length 会在路线找不到的情况下，返回 INFINITY_ROUTE_LENGTH
   要对这个特殊值进行判断！

"""

__all__ = [

    "find_shortest_route_for_move",
    "find_shortest_route_for_shoot",
    "get_route_length",

    "get_searching_directions",

    "DIRECTIONS_URDL", "DIRECTIONS_ULDR", "DIRECTIONS_DRUL", "DIRECTIONS_DLUR",
    "DIRECTIONS_RULD", "DIRECTIONS_LURD", "DIRECTIONS_RDLU", "DIRECTIONS_LDRU",

    "DEFAULT_BLOCK_TYPES",
    "DEFAULT_DESTROYABLE_TYPES"

    "INFINITY_WEIGHT",
    "INFINITY_ROUTE_LENGTH",

    "NONE_ACTION_ON_BFS",
    "MOVE_ACTION_ON_BFS",
    "SHOOT_ACTION_ON_BFS",

    ]

from ..const import DEBUG_MODE, MAP_WIDTH, MAP_HEIGHT
from ..global_ import np, deque
from ..utils import debug_print, debug_pprint
from ..field import Field, BASE_FIELD_TYPES, TANK_FIELD_TYPES

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

INFINITY_WEIGHT       = -1 # 无穷大的权重，相当于不允许到达
INFINITY_ROUTE_LENGTH = -1 # 无穷大的路径长度，相当于无法找到

DUMMY_ACTION_ON_BFS = -2 # 空行为
NONE_ACTION_ON_BFS  = -1 #　上回合什么都不做，相当于停止，专门用于 start == end 的情况
MOVE_ACTION_ON_BFS  = 0  # 上一回合操作标记为搜索
SHOOT_ACTION_ON_BFS = 1  # 上一回合操作标记为射击


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


def _BFS_search_for_move(start, end, map_matrix_T, weight_matrix_T,
                         block_types=DEFAULT_BLOCK_TYPES, x_axis_first=False,
                         middle_first=False):
    """
    BFS 搜索从 start -> end 的最短路径，带权重
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

    Return:

        - dummy_tail        Node        end 节点后的空节点：
                                        -------------------
                                        1. 如果本次搜索找到路径，则其 parent 属性指向 end 节点，
                                        可以连成一条 endNode -> startNode 的路径。
                                        2. 如果传入的 start == end 则 startNode == endNode
                                        这个节点的 parent 指向 startNode 。
                                        3. 如果没有搜索到可以到达的路线，则其 parent 值为 None

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

    '''
    debug_print("map:\n", matrixMap.T)
    debug_print("weight:\n", matrixWeight.T)
    debug_print("can move on:\n", matrixCanMoveTo.astype(np.int8).T)
    '''

    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION_ON_BFS,
        ]

    dummyTail = [ # end 节点后的空节点
        (-1, -1),
        None, #　当找到 end 的时候，这个值指向 end，否则保持为 None
        -1,
        -1,
        DUMMY_ACTION_ON_BFS,
        ]

    queue  = deque() # queue( [Node] )
    matrixMarked = np.zeros_like(matrixMap, dtype=np.bool8)

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init

    while len(queue) > 0:

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if matrixMarked[x, y]:
            continue
        matrixMarked[x, y] = True

        if DEBUG_MODE:
            matrixDistance[x, y] = _get_route_length_by_node_chain(node)

        if (x, y) == end: # 到达终点
            dummyTail[1] = node
            break

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
                MOVE_ACTION_ON_BFS,
                ])
    '''
    if DEBUG_MODE:
        debug_print("distance matrix:\n", matrixDistance.T)
    '''

    return dummyTail


def _BFS_search_for_shoot(start, end, map_matrix_T, move_weight_matrix_T,
                          shoot_weight_matrix_T, block_types=DEFAULT_BLOCK_TYPES,
                          destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                          x_axis_first=False, middle_first=False):
    """
    BFS 搜索从 start 开始到击中 end 的最短路线，带权重
    ----------------------------------------------------------------------------

    实现思路：

    首先，我们可以认为，射击的方式能够比移动的方式更快地接近目标，毕竟炮弹是飞行的。
    而能够直接向目标发动射击的位置，仅仅位于与它同一行或同一列的位置上，因此，搜索的思路是，
    对于所有可以向目标发起进攻的坐标，分别找到从起点移动到这些坐标的最短路径，然后接着以射击
    的方式，找到从这些射击点到达目标点的路径（这种路径可以抽象地认为是炮弹飞行的路径），
    然后从中找到最短的一条路径（对于射击来讲，距离可以理解为就是开炮和冷却的回合），
    该路径即为所求的。

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

    Return:

        - dummy_tail        Node        end 节点后的空节点：
                                        -------------------
                                        1. 如果本次搜索找到路径，则其 parent 属性指向 end 节点，
                                        可以连成一条 endNode -> startNode 的路径。
                                        2. 如果传入的 start == end 则 startNode == endNode
                                        这个节点的 parent 指向 startNode 。
                                        3. 如果没有搜索到可以到达的路线，则其 parent 值为 None

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
            elif not matrixCanBeDestroyed[x, y]:
                break
            matrixCanShoot[x, y] = True


    #debug_print("map:\n", matrixMap.T)
    #debug_print("weight of move:\n", matrixMoveWeight.T)
    #debug_print("weight of shoot:\n", matrixShootWeight.T)
    #debug_print("can move to:\n", matrixCanMoveTo.astype(np.int8).T)
    #debug_print("can shoot:\n", matrixCanShoot.astype(np.int8).T)
    #debug_print("can be destroyed:\n", matrixCanBeDestroyed.astype(np.int8).T)


    startNode = [
        (x1, y1),
        None,
        0, # 初始节点本来就已经到达了
        0, # 初始节点不耗费步数
        NONE_ACTION_ON_BFS, # 对于 start == end 的情况，将返回 startNode，相当于原地等待
        ]

    dummyTail = [
        (-1, -1),
        None,
        -1,
        -1,
        DUMMY_ACTION_ON_BFS,
        ]

    queue  = deque() # queue( [Node] )
    matrixMarked = np.zeros_like(matrixMap, dtype=np.bool8)
    canShootNodeChains = {} # { (x, y): Node } 从 start 到每一个可射击点的最短路线

    if DEBUG_MODE:
        matrixDistance = np.full_like(matrixMap, -1)

    queue.append(startNode) # init


    ## 首先通过常规的 BFS 搜索，确定到达每一个射击点的最短路径

    while len(queue) > 0:

        node = queue.popleft()

        if node[2] > 0: # 还剩 step 步
            node[2] -= 1
            queue.append(node) # 相当于下一个节点
            continue

        x, y = node[0]

        if matrixMarked[x, y]:
            continue
        matrixMarked[x, y] = True

        if matrixCanShoot[x, y]:
            canShootNodeChains[(x, y)] = node  # 记录最短节点

        if DEBUG_MODE:
            matrixDistance[x, y] = _get_route_length_by_node_chain(node)

        for dx, dy in get_searching_directions(x1, y1, x2, y2,
                                               x_axis_first=x_axis_first,
                                               middle_first=middle_first):
            x, y = node[0]
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
                MOVE_ACTION_ON_BFS,
                ])


    #if start == (6, 0):
    #    debug_print("distance matrix:\n", matrixDistance.T)


    ## 接下来对于每个节点，尝试通过射击的方式走完剩下的路程

    reachTargetNodeChains = [] # 收集所有可以成功射击到基地的路线

    for xy, node in canShootNodeChains.items():

        if xy == end:
            reachTargetNodeChains.append(node)
            continue

        # 确定攻击方向
        x3, y3 = xy
        dx = np.sign(x2 - x3)
        dy = np.sign(y2 - y3)

        while True:
            x3 += dx
            y3 += dy
            weight = matrixShootWeight[x3, y3]

            node = [ # 走到下一个节点
                (x3, y3),
                node,
                weight-1, # 补偿
                weight,
                SHOOT_ACTION_ON_BFS,
                ]

            if (x3, y3) == end: # 到达目标
                reachTargetNodeChains.append(node)
                break

    #debug_print( [_get_route_length_by_node_chain(node) for node in reachTargetNodeChains] )


    ## 找到最短的路径

    if len(reachTargetNodeChains) > 0: # BUG Fix: 只有在存在路线的情况下才能用 min
        dummyTail[1] = min(reachTargetNodeChains, # 最短路径
                        key=lambda node: _get_route_length_by_node_chain(node))

    return dummyTail


def find_shortest_route_for_move(start, end, matrix_T, block_types=DEFAULT_BLOCK_TYPES,
                                 x_axis_first=False, middle_first=False):
    """
    搜索移动到目标的最短路线

    Input:
        - matrix_T   np.array( [[int]] )   游戏地图的类型矩阵的转置

    Return:
        - route   [(x: int, y: int, weight: int, BFSAction: int)]   带权重值的路径
    """
    matrixMap = matrix_T

    matrixWeight = np.ones_like(matrixMap)
    matrixWeight[matrixMap == Field.BRICK] = 1 + 1 # 射击一回合，移动一回合
    matrixWeight[matrixMap == Field.STEEL] = INFINITY_WEIGHT
    matrixWeight[matrixMap == Field.WATER] = INFINITY_WEIGHT

    dummyTail = _BFS_search_for_move(start, end, matrixMap, matrixWeight,
                                    block_types=block_types,
                                    x_axis_first=x_axis_first,
                                    middle_first=middle_first)

    route = []
    node = dummyTail
    while True:
        node = node[1]
        if node is not None:
            x, y      = node[0]
            weight    = node[3]
            BFSAction = node[4]
            route.append( (x, y, weight, BFSAction) )
        else:
            break
    route.reverse()
    return route


def find_shortest_route_for_shoot(start, end, matrix_T,
                                  block_types=DEFAULT_BLOCK_TYPES,
                                  destroyable_types=DEFAULT_DESTROYABLE_TYPES,
                                  x_axis_first=False,
                                  middle_first=False):
    """
    搜索移动并射击掉目标的最短路线

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


    dummyTail = _BFS_search_for_shoot(start, end, matrixMap, matrixMoveWeight,
                                    matrixShootWeight,
                                    block_types=block_types,
                                    destroyable_types=destroyable_types,
                                    x_axis_first=x_axis_first,
                                    middle_first=False)
    route = []
    node = dummyTail
    while True:
        node = node[1]
        if node is not None:
            x, y      = node[0]
            weight    = node[3]
            BFSAction = node[4]
            route.append( (x, y, weight, BFSAction) )
        else:
            break
    route.reverse()
    return route


def get_route_length(route):
    """
    计算路线长度

    Input:
        - route    [(x: int, y: int, weight: int, BFSAction: int)]   带权重值的路径，从 start -> end

    Return:
        - length   int   路线长度，如果是空路线，返回 无穷大长度
    """
    if len(route) == 0:
        return INFINITY_ROUTE_LENGTH
    return np.sum( r[2] for r in route )


def _get_route_length_by_node_chain(node):
    """
    [DEBUG] 传入 node head ，计算其所代表的节点链对应的距离
    """
    assert isinstance(node, list) and len(node) == 5
    dummyTail = [
        (-1, -1),
        node,
        -1,
        -1,
        DUMMY_ACTION_ON_BFS,
        ]
    route = []
    node = dummyTail
    while True:
        node = node[1]
        if node is not None:
            x, y   = node[0]
            weight = node[3]
            route.append( (x, y, weight) )
        else:
            break
    return get_route_length(route)


#{ END }#