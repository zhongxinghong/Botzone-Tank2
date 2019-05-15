# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-29 23:02:34
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-15 17:20:20
"""
状况评估
"""

__all__ = [

    "evaluate_aggressive",
    "estimate_route_similarity",

    ]

from ..global_ import np
from ..utils import debug_print, simulator_print
from .utils import get_manhattan_distance
from .status import Status

#{ BEGIN }#

def evaluate_aggressive(battler, oppBattler):
    """
    根据敌我两架坦克的攻击线路长短，衡量当前侵略性

    Input:
        - battler      BattleTank
        - oppBattler   BattleTank

    Return:
        [status]
        - Status.AGGRESSIVE   我方处于攻击状态
        - Status.DEFENSIVE    我方处于防御状态
        - Status.STALEMENT    双方处于僵持状态
    """
    myRoute = battler.get_shortest_attacking_route()
    oppRoute = oppBattler.get_shortest_attacking_route()
    #
    # TODO:
    #   阈值不可定的太小，否则可能是错误估计，因为对方如果有防守，
    #   就有可能拖延步数。很有可能需要再动态决策一下，尝试往前预测几步，看看
    #   会不会受到阻碍，然后再下一个定论
    #
    assert not myRoute.is_not_found() and not oppRoute.is_not_found(), "route not found"

    leadingLength = oppRoute.length - myRoute.length

    # debug_print(battler, oppBattler, "leading:", leadingLength)

    if battler.is_in_enemy_site(): # 在敌方半边地图，更倾向于不防御

        if leadingLength >= 1:
            return Status.AGGRESSIVE
        elif leadingLength < -2:
            return Status.DEFENSIVE
        else:
            return Status.STALEMENT

    else: # 在我方半边地盘，会增加防御的可能性

        if leadingLength >= 1:
            return Status.AGGRESSIVE
        elif leadingLength <= -1:
            return Status.DEFENSIVE
        else:
            return Status.STALEMENT


def estimate_route_similarity(route1, route2):
    """
    评估两条路线的相似度
    一般用于判断选择某条路线是否可以和敌人相遇

    实现思路：
    --------------
    首先找出两者中最短的一条路径，对于其上每一个点，在另一条路上寻找与之距离最短（曼哈顿距离即可）
    的点，并将这两个点之间的距离作为总距离的一个部分，每个分距离和相应点的权重的加权平均值即为总距离

    最后的估值为 总距离除以最短路线的坐标点数的均值 的倒数
    值越接近 1 表示越相近，值越接近 0 表示越不相近

    根据实际情景的需要，我们将较长路劲多出来的那些点忽略 ...


    TODO:
    -------------
    1. 如何考虑坐标权重
    2. 如何考虑长路径中多出来的那些点

    """
    route1 = [ (node.x, node.y, node.weight) for node in route1 ]
    route2 = [ (node.x, node.y, node.weight) for node in route2 ]

    if len(route1) > len(route2): # 确保 route1 坐标数不超过 route2
        route1, route2 = route2, route1

    total = 0
    for x1, y1, weight in route1:
        d = np.min([ get_manhattan_distance(x1, y1, x2, y2) for x2, y2, _ in route2 ])
        total += d * weight

    return 1 / ( total / len(route1) + 1 )

#{ END }#