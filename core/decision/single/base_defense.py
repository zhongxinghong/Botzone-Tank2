# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-15 17:32:08
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-24 17:36:07

__all__ = [

    "BaseDefenseDecision",

    ]

from ..abstract import SingleDecisionMaker
from ...utils import debug_print
from ...action import Action
from ...strategy.status import Status

#{ BEGIN }#

class BaseDefenseDecision(SingleDecisionMaker):
    """
    主动防守基地
    ---------------------
    现在没有和敌人正面相遇，首先先处理一种特殊情况

    在敌人就要攻击我方基地的情况下，应该优先移动，而非预判击杀
    这种防御性可能会带有自杀性质


    若敌人当前回合正面对我方基地
    ----------------------------
    1. 敌人当前回合炮弹冷却，下回合射向我方基地，如果我方坦克下一步可以拦截，那么优先移动拦截
    2. 敌人当前回合可以射击，我方坦克下一步可以拦截，那么自杀性拦截
    3. 敌人当前回合炮弹冷却，下回合射向我方基地，而我方坦克需要两步才能拦截，那么自杀性拦截


    若敌人下一回合可以面对我方基地
    ----------------------------
    1. 此时敌人必定可以射击，如果我方坦克在这一步可以优先移动到拦截的位置，那么优先移动

    """
    def _make_decision(self):

        player  = self._player
        map_    = player._map
        battler = player.battler


        for oppBattler in [ _oppPlayer.battler for _oppPlayer in player.opponents ]:
            if oppBattler.destroyed:
                continue

            #
            # 敌人当前回合面向基地
            #
            if oppBattler.is_face_to_enemy_base():
                if oppBattler.canShoot: # 敌方可以射击
                    for action in battler.get_all_valid_move_action():
                        with map_.simulate_one_action(battler, action):
                            if not oppBattler.is_face_to_enemy_base(): # 此时不再面向我方基地，为正确路线
                                player.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                return action
                else: # 敌方不可射击
                    for action in battler.get_all_valid_move_action(): # 敌方不能射击，我方尝试移动两步
                        with map_.simulate_one_action(battler, action):
                            if not oppBattler.is_face_to_enemy_base(): # 一步防御成功
                                player.set_status(Status.BLOCK_ROAD_FOR_OUR_BASE)
                                return action
                            else: # 尝试两步拦截
                                if map_.is_valid_move_action(battler, action): # 需要先预判是否合理
                                    with map_.simulate_one_action(battler, action):
                                        if not oppBattler.is_face_to_enemy_base(): # 两步拦截成功
                                            player.set_status(Status.SACRIFICE_FOR_OUR_BASE)
                                            return action
            else:
                #
                # 敌人下一回合可能面向基地
                #
                for enemyAction in oppBattler.get_all_valid_move_action():
                    with map_.simulate_one_action(oppBattler, enemyAction):
                        if oppBattler.is_face_to_enemy_base(): # 敌人移动一步后面向我方基地
                            for action in battler.get_all_valid_move_action():
                                with map_.simulate_one_action(battler, action):
                                    if not oppBattler.is_face_to_enemy_base(): # 我方优先移动可以阻止
                                        player.set_status(Status.BLOCK_ROAD_FOR_OUR_BASE)
                                        return action

#{ END }#