# -*- coding: utf-8 -*-
# @Author: zhongxinghong
# @Date:   2019-05-27 21:21:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-28 17:08:59

__all__ = [

    "CooperativeAttackTeamDecision",

    ]

from ..abstract import TeamDecisionMaker
from ...utils import debug_print
from ...action import Action
from ...field import BrickField
from ...strategy.status import Status

#{ BEGIN }#

class CooperativeAttackTeamDecision(TeamDecisionMaker):
    """
    团队合作拆家策略
    -----------------

    案例
    ------------
    1.  5ceacbd0811959055e22139d   需要预判 1 步  -> 5cec07f30df42d28e72de8d8
    2.  5ce8db66d2337e01c7ab9fae   需要预判 3 步  -> 5cec1a324742030582fad728
    3.  5cec9157641dd10fdcc5f30d   重叠进攻时能够分开射击了
    4.  5cec9a19641dd10fdcc5ff9f   case 3 的另一种实现，提前找到合作路线
    5.  5cec9c10641dd10fdcc60254   case 2 的另一种实现
    6.  5cec9d01641dd10fdcc6045a   合作与不合作路线相同，但是选择了合作
    7.  5cec9d7f641dd10fdcc60556
    8.  5ceca04d641dd10fdcc60aed   case 2 的另一种实现，但是路线更短，因为将合作触发条件放宽到非严格过中线！
    9.  5ceca0ab641dd10fdcc60bb6   将合作条件放宽到非严格过中线可以触发的合作拆家
    10. 5ceca21b641dd10fdcc60d4d
    11. 5ceca3c3641dd10fdcc61071
    12. 5ceca80d641dd10fdcc617e9
    13. 5cecabbd641dd10fdcc61d34
    14. 5cecfa94641dd10fdcc69661

    触发前提
    --------------
    在双方均到达对方基地的前提下，假定双方坦克不会再发生交火。在这种情况下，可以认为找到的
    最短路线即为实际可走的、不受敌方影响的最短路线。那么可以进行团队合作，寻找一条两人合作下
    距离更加短的进攻路线


    实现方法
    --------------
    下面给出一种简单的实现方法（只预判一回合，更加复杂的情况尚未能实现）

    这个策略中存在主攻队员和辅助队员的角色划分。这个并不能在一开始就得出定论，而是要通过判断。

    首先，合作拆家所希望达到的效果是，辅助队员帮助主攻队员清除其路线上的土墙，从而减短主攻队员的
    攻击路线长度。每清除掉一个土墙，能够减少的路径长度为 2

    因此，首先在 delay = 1 的限制条件下，找到其中一个进攻队员所有可能的最短路线。 delay = 1 是允许的，
    因为一个土墙的权重是 2 ，打掉 delay = 1 的路线上的一个土墙，可以得到比 delay = 0 的最短路线更加短的路线。
    然后考虑另一个进攻队员当前回合所有可能的攻击行为。找到这些攻击行为下能够摧毁掉的 fields ，如果恰好是
    位于另一队员攻击路线上的土墙，那么就找到了一条双人合作下的更短路线。

    依照上述方法，可以列举出所有可能的最短路线。对这些路线长度进行排序以找到最短的路线，即为团队合作下更优
    的一种拆家路线。


    补充的更复杂实现
    -----------------
    有的时候会出现两个队友攻击路线相同且刚好互相不会影响 5ce8db66d2337e01c7ab9fae ，这种情况下实际上仍然
    有机会产生团队合作，但是需要预判 3 步，第一步首先考虑所有可能的进攻行为，第二步按照正常的进攻方向，第三步
    再尝试寻找团队更优路线，如果此时可以找到团队合作路线，那么当前回合就先采用第一步的进攻行为。第二步照常进攻
    到了第三步的时候就会被上面那种单回合的合作拆家决策找到合作路线。


    特判情况
    -----------
    1. 考虑这样一种情况，当前两个队友进攻路线长度相同，两者下一步同时攻击一个块，假如让其中一个坦克停止攻击
    在下回合可以得到更加短的进攻路线，那么就让这个队员暂时停下来。这种情况通常对应着最后拆基地的几步，一个队员
    暂时停下来，让另一个队员拆到前面的墙，然后他下回合马上可以打掉基地，最短路线长度是 2 ，
    如果双方此时是同时开火的，那么最短路线长度是 3

    2. 假设一个队友这回合打掉墙，另一个队友下回合可以到达这个队友身后，下回合前面的队友闪避，后面的队友射击，
    那么最短路线长度是 2 ，如果此时前一个队员等待一回合，后面的队员将无法射击，那么最短路线长度将是 3

    """
    IS_MIDDLE_FIRST = True # 优先中路搜索
    IS_X_AXIS_FIRST = True # 优先 x-轴优先搜索

    def _find_cooperative_solution(self, attackingPlayer, assistantPlayer):
        """
        给定 attackingPlayer 和 assistantPlayer ，尝试寻找一种最短的进攻路线
        如果有个可行的方案，那么只返回找到的第一个

        Return:
            - solution   (attackingPlayer, route, realAction, assistantPlayer, shootAction) / None

        """
        team = self._team
        map_ = team._map
        oppBase = map_.bases[1 - team.side]

        IS_MIDDLE_FIRST = self.__class__.IS_MIDDLE_FIRST
        IS_X_AXIS_FIRST = self.__class__.IS_X_AXIS_FIRST

        attackingBattler = attackingPlayer.battler
        assistantBattler = assistantPlayer.battler

        for route in attackingBattler.get_all_shortest_attacking_routes(delay=1, middle_first=IS_MIDDLE_FIRST, x_axis_first=IS_X_AXIS_FIRST):
            for shootAction in assistantBattler.get_all_valid_shoot_actions():
                destroyedFields = assistantBattler.get_destroyed_fields_if_shoot(shootAction)
                if len(destroyedFields) == 1:
                    field = destroyedFields[0]
                    if isinstance(field, BrickField) and field.xy in route: # 拆到了一个队友进攻路线上的土墙
                        #
                        # 首先考虑打掉的是不是同一个块
                        #
                        # 打掉同一个块的情况下，当且仅当攻击方已经面向对方基地时有效，否则起不到增加长度的效果
                        #
                        attackAction = attackingBattler.get_next_attacking_action(route)
                        if Action.is_shoot(attackAction):
                            destroyedFields2 = attackingBattler.get_destroyed_fields_if_shoot(attackAction)
                            if len(destroyedFields2) == 1 and destroyedFields2[0] is field: # 打掉的是同一个块
                                if not attackingBattler.on_the_same_line_with(oppBase, ignore_brick=True):
                                    continue # 只有当攻击方面对对方基地时，才能起到减少路线长度的效果
                                else: # 否则可以让攻击方这回合等待
                                    realAction = Action.STAY
                                    return (attackingPlayer, route, realAction, assistantPlayer, shootAction)

                        realAction = attackingPlayer.try_make_decision(attackAction)
                        if not Action.is_stay(realAction):
                            return (attackingPlayer, route, realAction, assistantPlayer, shootAction)

        # 找不到，返回 None
        return None


    def _make_decision(self):

        team = self._team
        map_ = team._map
        oppBase = map_.bases[1 - team.side]
        player1, player2 = team.players
        returnActions = [ player.get_current_decision() for player in team.players ]

        if player1.defeated or player2.defeated: # 不是两个人就不需要考虑合作了
            return returnActions
        elif ( not player1.battler.is_in_enemy_site(include_midline=True)
            or not player2.battler.is_in_enemy_site(include_midline=True)
            ): # 两者必须同时在对方基地，并且是严格的不包含中线
               #
               # 条件放宽了，现在允许包含中线 5cec9e9d641dd10fdcc60783
               #
            return returnActions
        elif ( player1.has_status(Status.ENCOUNT_ENEMY)
            or player2.has_status(Status.ENCOUNT_ENEMY)
            or player1.has_status(Status.WAIT_FOR_MARCHING)
            or player2.has_status(Status.WAIT_FOR_MARCHING)
            or player1.has_status(Status.PREVENT_BEING_KILLED)
            or player2.has_status(Status.PREVENT_BEING_KILLED)
            ): # 不可以拥有和敌人遭遇战斗相关的状态
            return returnActions

        IS_MIDDLE_FIRST = self.__class__.IS_MIDDLE_FIRST
        IS_X_AXIS_FIRST = self.__class__.IS_X_AXIS_FIRST

        #
        # 不需要判断是否具有团队信号?
        #
        # 事实上他碰巧提供了一个很好的案例 5cec9157641dd10fdcc5f30d
        # 最后一步的时候由于覆盖了 READY_TO_LEAVE_TEAMMATE 的团队策略，使得最后一步合作得以顺利实现！
        #

        solutions = [] # -> [ (attackingPlayer, route, realAction, assistantPlayer, shootAction) ]

        for attackingPlayer, assistantPlayer in [ (player1, player2), (player2, player1) ]:
            attackingBattler = attackingPlayer.battler
            assistantBattler = assistantPlayer.battler

            if not assistantBattler.canShoot: # 当前回合不能进攻，那就无法发起协助了 ...
                continue

            _route1 = attackingBattler.get_shortest_attacking_route()
            _route2 = assistantBattler.get_shortest_attacking_route()
            minRouteLength = min(_route1.length, _route2.length)
            #
            # 攻击方进攻路线长度比辅助方长 2 步以上，那么直接跳过
            #--------------------------------------------------------
            # 因为单回合决策下至多可以让一个队员的路线长度减 2，如果进攻方比辅助方的攻击路线长 2 步以上，那么
            # 一回合内无论如何都不可能让进攻方的路线长度短于辅助方当前回合的最短路线长度，在这种情况下即使可以
            # 发生合作，也是没有意义的，甚至可能拖延辅助方的进攻节奏（但是并不能排除可以多回合帮助，然而这个情况
            # 非常复杂，所以在此不考虑了）
            #
            if _route1.length - _route2.length >= 2:
                continue

            solution = self._find_cooperative_solution(attackingPlayer, assistantPlayer)
            if solution is not None:
                solutions.append(solution)

            with map_.auto_revert() as counter:
                #
                # 现在往后模拟两回合 5ce8db66d2337e01c7ab9fae
                #
                # 第一步随便攻击，第二步按照正常的攻击方向，第三步看是否有合适的攻击路线
                #
                _cachedActions = set() # 缓存已经尝试过的第一步两个方向
                for route1 in attackingBattler.get_all_shortest_attacking_routes(delay=1, middle_first=IS_MIDDLE_FIRST, x_axis_first=IS_X_AXIS_FIRST): # 攻击方第一步允许 delay = 1
                    action1 = attackingBattler.get_next_attacking_action(route1)
                    realAction1 = attackingPlayer.try_make_decision(action1)
                    if Action.is_stay(realAction1):
                        continue
                    for route2 in assistantBattler.get_all_shortest_attacking_routes(middle_first=IS_MIDDLE_FIRST, x_axis_first=IS_X_AXIS_FIRST):
                        action2 = assistantBattler.get_next_attacking_action(route2)
                        realAction2 = assistantPlayer.try_make_decision(action2)
                        if Action.is_stay(realAction2):
                            continue
                        key = (action1, action2)
                        if key in _cachedActions:
                            continue
                        _cachedActions.add(key)
                        with map_.auto_revert() as counter:
                            ## 模拟两步 ##
                            map_.multi_simulate((attackingBattler, action1), (assistantBattler, action2))
                            counter.increase()
                            # 模拟两步找到路线
                            solution = self._find_cooperative_solution(attackingPlayer, assistantPlayer)
                            if solution is not None:
                                solutions.append( (attackingPlayer, route1, action1, assistantPlayer, action2) )
                                continue
                            ## 模拟三步 ##
                            action11 = attackingBattler.get_next_attacking_action()
                            action22 = assistantBattler.get_next_attacking_action()
                            map_.multi_simulate((attackingBattler, action11), (assistantBattler, action22))
                            counter.increase()
                            # 模拟三步找到路线
                            solution = self._find_cooperative_solution(attackingPlayer, assistantPlayer)
                            if solution is not None:
                                solutions.append( (attackingPlayer, route1, action1, assistantPlayer, action2) )
                                continue

        if len(solutions) > 0:
            solutions.sort(key=lambda tup: tup[1].length)

            for attackingPlayer, route, realAction, assistantPlayer, shootAction in solutions:
                attackingBattler = attackingPlayer.battler
                assistantBattler = assistantPlayer.battler
                returnActions[attackingBattler.id] = realAction
                returnActions[assistantBattler.id] = shootAction
                attackingPlayer.set_current_attacking_route(route)
                attackingPlayer.set_current_decision(realAction)
                attackingPlayer.set_team_decision(realAction)
                assistantPlayer.set_current_decision(shootAction)
                assistantPlayer.set_team_decision(shootAction)
                assistantPlayer.set_status(Status.HELP_TEAMMATE_ATTACK)
                break

        return returnActions

#{ END }#