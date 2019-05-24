# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-23 22:59:59
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 06:51:37

__all__ = [

    "FollowEnemyBehindBrickDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...global_ import np
from ...action import Action
from ...strategy.status import Status

#{ BEGIN }#

class FollowEnemyBehindBrickDecision(SingleDecisionMaker):
    """
    跟随墙后敌人的逻辑
    -----------------
    如果上回合敌人和我方隔墙僵持，然后敌人向两侧移动，为了防止敌人从旁边的墙突破，
    这里添加一个主动跟随的逻辑，假如对方这回合破墙，那么我方这回合就会出现在对方墙后，
    这样对方就无法进攻，甚至可以为我方进攻创造机会 5ce57677d2337e01c7a7c1ff

    """
    def _make_decision(self):

        player  = self._player
        map_    = player._map
        battler = player.battler

        Tank2Player = type(player)
        BattleTank  = type(battler)

        if (player.has_status_in_previous_turns(Status.HAS_ENEMY_BEHIND_BRICK, turns=1)
            and not Action.is_move(player.get_previous_action(back=1))
            ): # 上回合墙后有人
            with map_.rollback_to_previous():
                action = battler.get_next_attack_action()
                if Action.is_stay(action):
                    return
                oppTank = battler.get_enemy_behind_brick(action, interval=-1) # 找到墙后敌人
                if oppTank is None:  # 理论上不会存在？
                    return

                oppBattler = BattleTank(oppTank)
                oppPlayer  = Tank2Player(oppBattler)

                dodgeActions = oppBattler.try_dodge(battler)


            previousAction = oppPlayer.get_previous_action(back=1)
            if Action.is_stay(previousAction):
                return

            if previousAction in dodgeActions: # 敌人上回合从墙后闪开
                realAction = player.try_make_decision(previousAction) # 尝试跟随敌人上回合的移动行为
                if Action.is_move(realAction):
                    player.set_status(Status.READY_TO_FOLLOW_ENEMY)
                    return realAction


        #
        # 将动作连续化，如果对方连续移动，那么可以考虑跟随
        #
        if player.has_status_in_previous_turns(Status.READY_TO_FOLLOW_ENEMY):
            oppTank = None
            with map_.auto_undo_revert() as counter: # 有可能要多回合回滚
                while map_.revert():
                    counter.increase()
                    action = battler.get_next_attack_action()
                    if Action.is_stay(action):
                        continue
                    oppTank = battler.get_enemy_behind_brick(action, interval=-1)
                    if oppTank is not None:
                        oppBattler = BattleTank(oppTank)
                        oppPlayer = Tank2Player(oppBattler)
                        break

            if oppTank is not None: # 理论上一定会找到敌人
                previousAction = oppPlayer.get_previous_action(back=1)
                lastAction = player.get_previous_action(back=1) # 上回合一定跟随移动
                # 确保敌人在贴着墙移动，否则就不必继续跟随了
                if np.abs(previousAction % 4 - lastAction % 4) in (0, 2): # 两次移动方向或相反
                    realAction = player.try_make_decision(previousAction) # 尝试跟随敌人上回合行为
                    if Action.is_move(realAction):
                        player.set_status(Status.READY_TO_FOLLOW_ENEMY)
                        return realAction


#{ END }#