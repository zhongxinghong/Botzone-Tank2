# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 01:01:30
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-03 05:47:42
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

from .utils import debug_print
from .action import Action
from .strategy.status import Status
from .strategy.signal import Signal

#{ BEGIN }#

class Team(object):

    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def make_decision(self, *args, **kwargs):
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
                "status":  [] # [ set(), set() ] 每轮的状态
                }
        self._memory = memory


    def dump_memory(self):
        memory = self._memory
        memory["status"].append([
                self._player1.get_status(),
                self._player2.get_status(),
                ])
        return memory

    def get_memory(self):
        return self._memory

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
        for i in range( len(allStatus) - 1 ,
                        len(allStatus) - 1 - turns,
                        -1 ): # 逆序
            previousStatus = allStatus[i][player.id]
            if previousStatus is None:
                return False
            elif status not in previousStatus:
                return False
        else:
            return True


    def make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """

        # 假装先让对方以自己的想法决策
        #-------------------------------
        # 分析对方的行为，可以对下一步的行为作出指导
        #
        for oppPlayer in self._opponentTeam.players:
            oppPlayer.make_decision()



        action1 = action2 = Action.INVALID
        signal1 = signal2 = Signal.NONE

        action3 = action4 = Action.INVALID # 中间变量
        signal3 = signal4 = Signal.NONE    # 中间变量


        # 我方玩家单独决策
        #------------------------------
        # 了解个人真实想法
        #

        action1, _ = self._player1.make_decision()
        action2, _ = self._player2.make_decision()

        returnActions = [ action1, action2 ]


        # TODO: 强攻信号
        #-----------------
        # 如果一个队友和一个敌人纠缠，一个敌人和我都在进攻，并且在是僵持模式
        # 在一些情况下有可能会触发防御，这个时候发强攻信号，减小安全性的判断


        # TODO: 追击信号
        #------------------
        # 如果对方明着就是要来拆家，那么发动追击信号，不要老是等人家走到底线了再去追杀 ...



        # 检查是否有队员处在僵持阶段
        #--------------------------
        # 1. 双方均在墙后僵持不前进因为
        #
        # TODO:
        #   乱破墙，然后防御模式写得又烂，等于送死 ...
        #
        # TODO:
        #   单人不要随便破墙，但是有条件的破墙还是可以的！
        #   如果两个人均被一个人牵制，那么完全可以来一个双人决策
        #
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (False and action == Action.STAY                                 # 当前回合处于等待状态
                and player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)  # 墙后有人造成的
                and player.has_status(Status.WAIT_FOR_MARCHING)       # 因此等待行军
                and not player.has_status(Status.DEFENSIVE) # 不要让防御性的队友随意破墙
                and not player.has_status(Status.REALODING) # 目前有弹药
                and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=2)
                ): # 上两回合也处于僵持状态

                # 触发的条件是一方隔墙，队友因为这两个人的僵持受到牵制
                #----------------------------------------------------
                teammate = player.battler.teammate
                teammateAction = returnActions[ 1 - idx ] # 队友
                if (#teammateAction == Action.STAY # 不一定需要，因为队友可能在努力拆外墙
                    True and teammate.has_status()
                    ):
                    pass

                # 准备破墙，留好后路
                #------------------
                action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_BRICK)
                if Signal.is_break(signal3):
                    continue

                if (signal3 == Signal.READY_TO_PREPARE_FOR_BREAK_BRICK
                    or signal3 == Signal.READY_TO_BREAK_BRICK
                    ): # 均为合适的行为
                    returnActions[idx] = action3 # 设置为凿墙动作


        # 主动打破重叠的信号
        #-------------------
        # 1. 很多时候只有主动打破重叠，才能制造机会！
        #
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (action == Action.STAY
                and player.has_status(Status.OVERLAP_WITH_ENEMY)  # 在等待敌人
                and not player.has_status(Status.REALODING)        # 确认一下有炮弹
                and self.has_status_in_previous_turns(player, Status.OVERLAP_WITH_ENEMY, turns=3)
                ): # 数个回合里一直在等待

                action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_OVERLAP)
                if Signal.is_break(signal3):
                    continue

                if signal3 == Signal.READY_TO_BREAK_OVERLAP:
                    returnActions[idx] = action3


        action1, action2 = returnActions

        if action1 == Action.INVALID:
            action1 = Action.STAY
        if action2 == Action.INVALID:
            action2 = Action.STAY
        return [ action1, action2 ]

#{ END }#
