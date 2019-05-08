# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-29 23:02:34
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-09 03:13:21
"""
状况评估
"""

__all__ = [

    "assess_aggressive",

    "MINIMAL_TURNS_FOR_ACTIVE_DEFENSIVE_DECISION"

    ]

from ..utils import debug_print, simulator_print
from .status import Status

#{ BEGIN }#

MINIMAL_TURNS_FOR_ACTIVE_DEFENSIVE_DECISION = 2


def assess_aggressive(battler, oppBattler):
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

#{ END }#