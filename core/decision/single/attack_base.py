# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 18:42:37
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 09:32:27

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

        # TODO:
        #   可能需要考虑一种特殊情况： 队友被杀，自己下一步打掉对方基地，但是对方下一步把我干掉
        #   这种情况下，即使我方拆掉对方基地也算平局。也许可以考虑先闪避一回合，然后再继续拆家。
        #

        if battler.is_face_to_enemy_base() and battler.canShoot:
            player.set_status(Status.READY_TO_ATTACK_BASE) # 特殊状态
            return battler.get_next_attacking_action() # 必定是射击 ...

#{ END }#