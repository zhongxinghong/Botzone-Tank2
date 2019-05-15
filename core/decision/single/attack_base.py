# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 18:42:37
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-15 18:51:50

__all__ = [

    "AttackBaseDecision",

    ]


from ..abstract import SingleDecisionMaker
from ...strategy.status import Status

#{ BEGIN }#

class AttackBaseDecision(SingleDecisionMaker):
    """
    特殊情况决策，当下一步就要拆掉敌方基地时

    """
    def _make_decision(self):

        player  = self._player
        battler = player._battler

        if battler.is_face_to_enemy_base() and battler.canShoot:
            player.set_status(Status.READY_TO_ATTACK_BASE) # 特殊状态
            return battler.get_next_attack_action() # 必定是射击 ...

#{ END }#