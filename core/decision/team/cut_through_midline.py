# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-28 18:13:12
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 04:32:14

__all__ = [

    "CutThroughMidlineTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...global_ import np
from ...utils import outer_label, debug_print
from ...action import Action
from ...field import BrickField
from ...strategy.status import Status

#{ BEGIN }#

class CutThroughMidlineTeamDecision(TeamDecisionMaker):
    """
    当我方队员与敌人在墙后僵持，并且不得不选择等待的时候
    考虑是否可以打通土墙，因为这个时候也许可以干扰另一路敌人的进攻路线

    """
    def _make_decision(self):

        team = self._team
        map_ = team._map
        base = map_.bases[team.side]
        Tank2Player = type(team.players[0])
        returnActions = [ player.get_current_decision() for player in team.players ]

        for player in team.players:

            #
            # 保守起见，先等待一回合
            #
            # TODO:
            #   有可能延误战机！ 5ced7ce1641dd10fdcc776b1
            #   这样才是对的 5ced7d66641dd10fdcc777ae
            #
            # if not player.has_status_in_previous_turns(Status.HAS_ENEMY_BEHIND_BRICK, turns=1):
            #     continue

            with outer_label() as OUTER_CONTINUE:
                action = player.get_current_decision()
                tank = player.tank
                battler = player.battler

                if player.has_team_decision() or player.defeated:
                    continue

                if (Action.is_stay(action)                                # 当前回合处于等待状态
                    and player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)  # 墙后有人造成的
                    and player.has_status(Status.WAIT_FOR_MARCHING)       # 因此等待行军
                    and battler.canShoot # 必须要能够射击
                    and battler.is_near_midline() # 只有中线附近的队友才会触发这个攻击条件
                    ):
                    _oppBattler = player.get_risky_enemy()
                    _oppPlayer = Tank2Player(_oppBattler)
                    # 实际考虑的是它的队员！
                    oppPlayer = _oppPlayer.teammate
                    oppBattler = oppPlayer.battler
                    oppTank = oppBattler.tank

                    if oppPlayer.defeated: # 对方已经输了，就不用管了 ...
                        continue

                    x1, y1 = battler.xy
                    dx = np.sign( base.x - x1 )
                    x2 = x1 + dx
                    y2 = y1
                    shootAction = Action.get_shoot_action(x1, y1, x2, y2)

                    if battler.will_destroy_a_brick_if_shoot(shootAction): # 将会打掉一个砖块
                        field = battler.get_destroyed_fields_if_shoot(shootAction)[0]
                        #
                        # 首先判断这一步射击是否会阻止敌人的移动
                        #
                        enemyAttackingRoute = oppBattler.get_shortest_attacking_route()
                        oppAction = oppBattler.get_next_attacking_action(enemyAttackingRoute)
                        oppRealAction = oppPlayer.try_make_decision(oppAction)
                        if (Action.is_move(oppAction)
                            and Action.is_stay(oppRealAction)
                            and oppPlayer.get_risky_enemy() is battler
                            ): # 敌人下回合打算行军，但是受到我方坦克的影响而停止
                            continue # 那就算了

                        #
                        # 判断是否摧毁了敌人进攻路线上的块
                        #
                        _dx = np.sign( base.x - field.x ) # 首先判断这个块是否和当前坦克处在不同测的地图上
                        if _dx != 0 and _dx != dx: # _dx == 0 表示 x = 4 中线的墙可以打掉
                            if field.xy in enemyAttackingRoute:
                                continue # 不要打掉这个块？


                        #
                        # 防止出现我方坦克打掉一个块，对方可以突然出现在 field 前
                        #
                        for enemyMoveAction in oppBattler.get_all_valid_move_actions():
                            with map_.simulate_multi_actions((battler, shootAction), (oppBattler, enemyMoveAction)):
                                if oppBattler.destroyed: # 好吧，还是要判断一下这种情况的 ...
                                    continue
                                for enemy in oppBattler.get_enemies_around():
                                    if enemy is tank:
                                        raise OUTER_CONTINUE

                        #
                        # 现在说明可以射击
                        #
                        player.set_status(Status.READY_TO_CUT_THROUGH_MIDLINE)
                        returnActions[player.id] = shootAction
                        player.set_team_decision(shootAction)

        return returnActions

#{ END }#