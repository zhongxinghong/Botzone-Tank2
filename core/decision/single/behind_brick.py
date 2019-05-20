# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-20 09:12:48
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-20 09:18:35

__all__ = [

    "BehindBrickDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...action import Action
from ...tank import BattleTank
from ...strategy.status import Status
from ...strategy.signal import Signal

#{ BEGIN }#

class BehindBrickDecision(SingleDecisionMaker):
    """
    适用于在墙后和敌人僵持时的决策

    """
    def _make_decision(self):

        player = self._player
        signal = self._signal
        battler = player.battler

        # (inserted) 准备破墙信号
        #--------------------------
        # 触发条件：
        #
        #   1. 对应于双方对峙，我方开好后路后触发某些条件强制破墙
        #   2. 对方刚刚从墙后移开，我方存在后路，这个时候强制破墙
        #
        # 收到这个信号的时候，首先检查是否可以闪避
        #
        #   1. 如果可以闪避，就返回可以破墙的信号
        #   2. 如果不可以闪避，就返回这回合准备后路的信号
        #
        if signal == Signal.PREPARE_FOR_BREAK_BRICK:
            player.set_status(Status.WAIT_FOR_MARCHING)      # 用于下回合触发
            player.set_status(Status.HAS_ENEMY_BEHIND_BRICK) # 用于下回合触发
            attackAction = battler.get_next_attack_action()
            oppTank = battler.get_enemy_behind_brick(attackAction, interval=-1)

            '''_undoRevertTurns = 0
            while oppTank is None: #　对应于敌方刚离开的那种触发条件
                # 可能存在多轮回滚，因为别人的策略和我们的不一样！
                # 给别人回滚的时候必须要考虑多回合！
                map_.revert()
                _undoRevertTurns += 1
                oppTank = battler.get_enemy_behind_brick(attackAction, interval=-1)'''

            player.set_risk_enemy(BattleTank(oppTank)) # 重新设置这个敌人！
            assert oppTank is not None
            dodgeActions = battler.try_dodge(oppTank)
            if len(dodgeActions) == 0:
                # 准备凿墙
                breakBrickActions = battler.break_brick_for_dodge(oppTank)
                if len(breakBrickActions) == 0: # 两边均不是土墙
                    res = ( Action.STAY, Signal.CANHANDLED ) # 不能处理，只好等待
                else:
                    player.set_status(Status.READY_TO_PREPARE_FOR_BREAK_BRICK)
                    res = ( breakBrickActions[0], Signal.READY_TO_PREPARE_FOR_BREAK_BRICK )
            else:
                # 可以闪避，那么回复团队一条消息，下一步是破墙动作
                shootAction = battler.shoot_to(oppTank)
                player.set_status(Status.READY_TO_BREAK_BRICK)
                res = ( shootAction, Signal.READY_TO_BREAK_BRICK )

            '''for _ in range(_undoRevertTurns):
                map_.undo_revert()'''

            return res

#{ END }#