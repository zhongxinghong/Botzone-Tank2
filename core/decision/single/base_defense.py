# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 17:32:08
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-15 18:53:50

__all__ = [

    "BaseDefenseDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...action import Action
from ...strategy.status import Status

#{ BEGIN }#

class BaseDefenseDecision(SingleDecisionMaker):
    """
    主动防守基地
    -----------------

    现在没有和敌人正面相遇
    在进入主动防御和行军之前，首先先处理一种特殊情况

    在敌人就要攻击我方基地的情况下，应该优先移动，而非预判击杀
    这种防御性可能会带有自杀性质

    1. 如果敌人当前回合炮弹冷却，下一炮就要射向基地，如果我方坦克下一步可以拦截
       那么优先移动拦截，而非防御

    2. 如果敌人当前回合马上可以开盘，那么仍然考虑拦截（自杀性）拦截，可以拖延时间
       如果此时另一个队友还有两步就拆完了，那么我方就有机会胜利

    """
    def _make_decision(self):

        player  = self._player
        map_    = player._map
        tank    = player.tank
        battler = player.battler

        for oppBattler in [ _oppPlayer.battler for _oppPlayer in player.opponents ]:
            if oppBattler.is_face_to_enemy_base(): # 面向基地
                if oppBattler.canShoot: # 敌方可以射击，我方如果一步内可以拦截，则自杀性防御
                    for action in Action.MOVE_ACTIONS: # 尝试所有可能的移动情况
                        if map_.is_valid_move_action(tank, action):
                            with map_.simulate_one_action(tank, action):
                                if not oppBattler.is_face_to_enemy_base(): # 此时不再面向我方基地，为正确路线
                                    player.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                    return action
                else: # 敌方不可射击
                    for action in Action.MOVE_ACTIONS: # 敌方不能射击，我方尝试移动两步
                        if map_.is_valid_move_action(tank, action):
                            with map_.simulate_one_action(tank, action):
                                if not oppBattler.is_face_to_enemy_base(): # 一步防御成功
                                    player.set_status(Status.BLOCK_ROAD_FOR_OUR_BASE)
                                    return action
                                else: # 尝试第二步
                                    if map_.is_valid_move_action(tank, action):
                                        with map_.simulate_one_action(tank, action):
                                            if not oppBattler.is_face_to_enemy_base(): # 两步防御成功
                                                player.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                                return action # 当前回合先移动一步，下回合则在此处按一步判定

#{ END }#