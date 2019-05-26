# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-20 07:21:31
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-26 01:36:58

__all__ = [

    "LeaveTeammateDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...action import Action
from ...strategy.status import Status
from ...strategy.signal import Signal

#{ BEGIN }#

class LeaveTeammateDecision(SingleDecisionMaker):
    """
    处理两人重叠的情况
    --------------------

    1. 尝试采用安全的移动行为离开队友
    2. 避免和队友采用相同的移动方向
    3. 尽量往不导致进攻路线增加的方向移动

    """
    def _make_decision(self):

        player   = self._player
        signal   = self._signal
        map_     = player._map
        battler  = player.battler
        teammate = player.teammate


        if signal == Signal.SHOULD_LEAVE_TEAMMATE:

            actions = []
            for action in battler.get_all_valid_move_actions():
                if not Action.is_move(player.try_make_decision(action)): # 存在风险
                    continue
                if action == teammate.get_current_decision(): # 不能与队友的移动方向相同！
                    continue
                actions.append(action)

            if len(actions) == 0: # 没有合理的离开行为 ...
                return ( Action.STAY, Signal.CANHANDLED )

            route1 = battler.get_shortest_attacking_route()
            deltaLengths = {} #  action -> deltaLength
            for action in actions:
                with map_.simulate_one_action(battler, action):
                    route2 = battler.get_shortest_attacking_route() # 必定有路？
                    deltaLengths[action] = route2.length - route1.length # 移动后进攻路线短变短者值小

            action = min( deltaLengths.items(), key=lambda kv: kv[1] )[0]
            player.set_status(Status.READY_TO_LEAVE_TEAMMATE)
            return ( action, Signal.READY_TO_LEAVE_TEAMMATE )

#{ END }#