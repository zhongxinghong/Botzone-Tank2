# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-29 23:02:34
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 19:28:14
"""
状况评估
"""

__all__ = [


    "AGGRESSIVE_STATUS",
    "STALEMATE_STATUS",
    "DEFENSIVE_STATUS",

    "assess_aggressive",

    ]

from ..utils import debug_print, simulator_print
from .bfs import get_route_length


#{ BEGIN }#

AGGRESSIVE_STATUS = 1
STALEMATE_STATUS  = 0
DEFENSIVE_STATUS  = -1


def assess_aggressive(battler, oppBattler):
    """
    根据敌我两架坦克的攻击线路长短，衡量当前侵略性

    Input:
        - battler      BattleTank
        - oppBattler   BattleTank

    Return:
        - AGGRESSIVE_STATUS   我方处于攻击状态
        - STALEMATE_STATUS    双方处于僵持状态
        - DEFENSIVE_STATUS    我方处于防御状态
    """
    myRoute = battler.get_shortest_attacking_route()
    oppRoute = oppBattler.get_shortest_attacking_route()
    myRouteLen = get_route_length(myRoute)
    oppRouteLen = get_route_length(oppRoute)
    simulator_print(battler, "delta routeLen:", oppRouteLen - myRouteLen)
    # TODO:
    #   阈值不可定的太小，否则可能是错误估计，因为对方如果有防守，
    #   就有可能拖延步数。很有可能需要再动态决策一下，尝试往前预测几步，看看
    #   会不会受到阻碍，然后再下一个定论
    if oppRouteLen - myRouteLen >= 1: # TODO: 阈值多少合理？
        return AGGRESSIVE_STATUS
    elif myRouteLen - oppRouteLen > 1: # TODO: 阈值？
        return DEFENSIVE_STATUS
    else:
        return STALEMATE_STATUS

#{ END }#