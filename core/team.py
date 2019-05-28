# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 01:01:30
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-29 02:56:11
"""
游戏团队类
--------------------------------------------
特点：
- 以全局的观点来决策
- 通过向 player 发信号来改变 player 的决策行为
- 具有多轮记忆，能够处理多轮决策的问题
- 团队类可以通过发起信号来协调团战问题


方式：
----------
团队首先让两个队员单独决策，并根据队友、敌人和全局的状况，对单人决策进行协调
团队和队员通过信号进行来回地沟通，反复决策，直到团队认为当前情况满意为止


注意：
------------
如果一个团队协调决策需要多轮，那么记得 Player 在受到信号后，需要重新设置触发
信号的状态

"""

__all__ = [

    "Tank2Team",

    ]

from .global_ import sys
from .utils import debug_print
from .action import Action
from .strategy.search import find_all_routes_for_move, find_all_routes_for_shoot
from .decision.abstract import DecisionMaker
from .decision.chain import DecisionChain
from .decision.team import TeamDecisionDummyEnding, IndividualTeamDecision, VitalTeamDecision,\
    BreakBrickTeamDecision, ForcedAttackTeamDecision, LeaveTeammateTeamDecision,\
    BackToHelpTeamDecision, PreventTeamHurtTeamDecision, CooperativeAttackTeamDecision,\
    CutThroughMidlineTeamDecision

#{ BEGIN }#

class Team(DecisionMaker):

    UNHANDLED_RESULT = [ Action.STAY, Action.STAY ] # 实际上不可能碰到 team 不能决策的情况，否则找谁决策呀 ...

    def __init__(self, *args, **kwargs):
        if __class__ is self.__class__:
            raise NotImplementedError

class Tank2Team(Team):

    def __init__(self, side, player1, player2, map):
        player1.set_team(self)
        player2.set_team(self)
        self._side = side
        self._map = map
        self._player1 = player1
        self._player2 = player2
        self._opponentTeam = None
        self._memory = {} # 团队记忆
        self._previousActions = [] # 历史行为

    @property
    def side(self):
        return self._side

    @property
    def players(self):
        return [ self._player1, self._player2 ]

    def load_memory(self, memory):
        """
        botzone 将 data 传入给 team 恢复记忆
        """
        if memory is None:
            memory = {
                "status": [], # [ set(), set() ] 每轮的状态
                "labels": [ set(), set() ], # [ set(), set() ] 已有的标记
                "previousRoute": [ None, None ]  # [ Route, Route ]
                }
        self._memory = memory
        self._player1.add_labels(*memory["labels"][0])
        self._player2.add_labels(*memory["labels"][1])


    def dump_memory(self):
        memory = self._memory
        memory["status"].append([
                self._player1.get_status(),
                self._player2.get_status(),
                ])
        memory["labels"] = [
                self._player1.get_labels(),
                self._player2.get_labels(),
                ]
        memory["previousRoute"] = [
                self._player1.get_current_attacking_route(),
                self._player2.get_current_attacking_route(),
                ]
        return memory

    def get_memory(self):
        return self._memory

    def set_previous_actions(self, previousActions):
        """
        由 botzone input 获得的过去动作，可以将其视为一种记忆
        """
        self._previousActions = previousActions

    def set_opponent_team(self, team):
        """
        设置对手团队

        Input:
            - team    Tank2Team
        """
        assert isinstance(team, self.__class__)
        self._opponentTeam = team

    def has_status_in_previous_turns(self, player, status, turns=1):
        """
        在曾经的一定回合里，某玩家是否拥有某个状态

        Input:
            - player   Player   玩家实例，不一定是本队的
            - status   int      状态编号
            - turns    int      向前检查多少回合

        """
        team = player.team
        memory = team.get_memory()
        allStatus = memory["status"]
        if len(allStatus) == 0:
            return False
        # TODO:
        #   还需要判断回合数是否超出一已知回合？
        for turn in range( len(allStatus) - 1 ,
                           len(allStatus) - 1 - turns,
                           -1 ): # 逆序
            try:
                previousStatus = allStatus[turn][player.id]
            except IndexError: # 可能 allStatus 为空
                return False
            if previousStatus is None:
                return False
            elif status not in previousStatus:
                return False
        else:
            return True

    def has_status_recently(self, player, status, turns):
        """
        最近的几回合内是否曾经拥有过某个状态

        """
        team = player.team
        memory = team.get_memory()
        allStatus = memory["status"]
        if len(allStatus) == 0:
            return False

        for turn in range( len(allStatus) - 1 ,
                           len(allStatus) - 1 - turns,
                           -1 ):
            try:
                previousStatus = allStatus[turn][player.id]
                if status in previousStatus:
                    return True
            except IndexError:
                return False
        else:
            return False

    def get_previous_action(self, player, back=1):
        """
        获得一个玩家的操纵坦克的历史行为

        Input:
            - player   Player       玩家实例，不一定是本队的
            - back     int ( >= 1)  前第几回合的历史记录，例如 back = 1 表示前一回合
        """
        assert back >= 1, "back >= 1 is required"
        return self._previousActions[player.id][-back]

    def get_previous_attcking_route(self, player):
        return self._memory[player.id]


    def _make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """
        team = self

        # 假装先让对方以自己的想法决策
        #-------------------------------
        # 分析对方的行为，可以对下一步的行为作出指导
        #
        for oppPlayer in self._opponentTeam.players:
            oppPlayer.make_decision()


        decisions = DecisionChain(

                    IndividualTeamDecision(team),
                    VitalTeamDecision(team),

                    LeaveTeammateTeamDecision(team),
                    ForcedAttackTeamDecision(team),
                    BreakBrickTeamDecision(team),
                    BackToHelpTeamDecision(team),
                    CutThroughMidlineTeamDecision(team),
                    CooperativeAttackTeamDecision(team),
                    PreventTeamHurtTeamDecision(team),

                    TeamDecisionDummyEnding(team),
                )

        res = decisions._make_decision()

        # for func in [ find_all_routes_for_shoot, find_all_routes_for_move ]:
        #     if not hasattr(func, "__wrapped__"):
        #         continue
        #     _wrapper = func.__wrapped__
        #     if hasattr(_wrapper, "__memory__"):
        #         _memory = _wrapper.__memory__
        #         debug_print(_memory.keys(), len(_memory))
        #         debug_print(sys.getsizeof(_memory))

        return res

    # @override
    def make_decision(self):
        """
        如果有的玩家无法决策，那么就将其行为设为 Action.STAY
        事实上这种情况是不应该出现的，但是为了防止出错，此处对决策结果进行检查

        """
        player1 = self._player1
        player2 = self._player2

        action1, action2 = self._make_decision()

        if not player1.is_handled(action1):
            action1 = Action.STAY
        if not player2.is_handled(action2):
            action2 = Action.STAY

        return [ action1, action2 ]

#{ END }#
