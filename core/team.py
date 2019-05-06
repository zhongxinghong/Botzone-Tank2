# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 01:01:30
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-07 04:37:37
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
from .player import Tank2Player

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

    def get_previous_action(self, player, back=1):
        """
        获得一个玩家的操纵坦克的历史行为

        Input:
            - player   Player       玩家实例，不一定是本队的
            - back     int ( >= 1)  前第几回合的历史记录，例如 back = 1 表示前一回合
        """
        assert back >= 1, "back >= 1 is required"
        return self._previousActions[player.side][player.id][-back]


    def make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """
        map_ = self._map

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

        returnActions  = [ action1, action2 ] # 实际的行为值

        # 是否已经存在团队命令？对于部分团队决策，如果队友已经有团队命令，则会跳过继续团队决策
        # ---------------------
        hasTeamActions = [ False, False ]



        # 存在以下特殊状态的队员
        # 其单独决策行为即为最优行为，不可协调
        #----------------------------------------------------
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (   player.has_status(Status.SACRIFICE_FOR_OUR_BASE)   # 准备为防御基地牺牲
                or player.has_status(Status.BLOCK_ROAD_FOR_OUR_BASE)  # 准备为防御基地堵路
                or player.has_status(Status.READY_TO_ATTACK_BASE)     # 准备攻击敌方基地
                or player.has_status(Status.READY_TO_KILL_ENEMY)      # 准备击杀敌人
                ):
                hasTeamActions[idx] = True
        # TODO:
        #   牺牲攻击局，可能需要考虑一下闪避 5ccca535a51e681f0e8c7131



        # 强攻信号
        #-----------------
        # 为了解决默认行为过于保守的问题。
        #
        # 在攻击过程中s，一些所谓的有潜在危险的行为，实际上一点危险都没有,但是为了防止出错，就原地等待，
        # 这反而是贻误了战机，甚至最后还要匆忙转攻为守，实际上根本就防不住
        #
        # 所以应该根据战场形势分析潜在风险究竟有多大，如果实际上是没有风险的，就发动强攻信号，让攻击者
        # 保持进攻，而不去过分规避风险
        #
        # 如下情况是值得发动强攻信号的：
        # 1. 侵略/僵持模式，出现了停止前进，防止被杀的状况
        #    - 敌人正在和队友交火，敌人此回合可以射击，但是下回合必定会攻击队友
        #    - 敌人正在和队友隔墙僵持，敌人可以射击，但是他并不攻击，多半是为了拖延战局
        #    - 敌人正在和队友重叠，敌人可以射击，但是他一直在等待队友决策
        # 2. 侵略/僵持模式，出现了停止前进，两方均越过了中线，对方明显不会回头，不想防你
        #
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (   player.has_status(Status.AGGRESSIVE)  # 侵略模式
                or player.has_status(Status.STALEMENT)   # 僵持模式
                ):
                if (action == Action.STAY # 但是出现了停止前进
                    and player.has_status(Status.WAIT_FOR_MARCHING)    # 等待行军
                    and player.has_status(Status.PREVENT_BEING_KILLED) # 是为了防止被杀
                    ):
                    shouldForcedMarch = False

                    playerRiskyEnemyBattler = player.get_risky_enemy_battler()
                    if playerRiskyEnemyBattler is None: # 说明是因为没有弹药？
                        continue
                    oppPlayer = Tank2Player(playerRiskyEnemyBattler)
                    teammate = player.teammate # 考虑队友和敌军的情况

                    #debug_print(player.get_risky_enemy_battler())
                    #debug_print(teammate.get_risky_enemy_battler())

                    # 敌人正在和队友交火
                    #------------------
                    # 这种情况直接前进
                    #
                    if (oppPlayer.has_status(Status.ENCOUNT_ENEMY)
                        and oppPlayer.has_status(Status.READY_TO_FIGHT_BACK)
                        and oppPlayer.get_risky_enemy_battler() is teammate.battler
                        ): # 说明对方正准备和队友交火
                        shouldForcedMarch = True

                    # 敌人正在和队友隔墙僵持
                    #----------------------
                    # 如果他们僵持了超过一回合以上
                    # 保守起见，等待一回合，如果对方并未攻击我，说明它更关心和队友僵持，或者故意在拖时间
                    #
                    # 那么可以直接进攻
                    #
                    elif (oppPlayer.has_status(Status.HAS_ENEMY_BEHIND_BRICK) # 僵持超过一回合
                        and self.has_status_in_previous_turns(oppPlayer, Status.HAS_ENEMY_BEHIND_BRICK, turns=1)
                        and oppPlayer.get_risky_enemy_battler() is teammate.battler
                        and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=1) # 已经等待了一回合
                        and self.has_status_in_previous_turns(player, Status.PREVENT_BEING_KILLED, turns=1)
                        ):
                        shouldForcedMarch = True

                    # 敌人正在和队友重叠
                    #----------------------------
                    # 如果他们重叠不动超过一回合以上
                    # 保守起见，等待一回合，如果对方并未攻击我，说明它更关心和队友重叠
                    #
                    # 那么可以直接进
                    #
                    elif (oppPlayer.has_status(Status.OVERLAP_WITH_ENEMY) # 僵持超过一回合
                        and self.has_status_in_previous_turns(oppPlayer, Status.OVERLAP_WITH_ENEMY, turns=1)
                        and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=1) # 已经等待了一回合
                        and self.has_status_in_previous_turns(player, Status.PREVENT_BEING_KILLED, turns=1)
                        ):
                        shouldForcedMarch = True

                    # 双方均跨过中线
                    #-----------------------------
                    # 那么不再反击，直接进攻？
                    #
                    # TODO:
                    #   存在着一攻一守的 bot
                    #

                    if shouldForcedMarch: # 建议强制行军
                        action3, signal3 = player.make_decision(Signal.FORCED_MARCH)
                        if Signal.is_break(signal3):
                            continue
                        if signal3 == Signal.READY_TO_FORCED_MARCH:
                            returnActions[idx] = action3
                            hasTeamActions[idx] = True



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
            if (action == Action.STAY                                 # 当前回合处于等待状态
                and player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)  # 墙后有人造成的
                and player.has_status(Status.WAIT_FOR_MARCHING)       # 因此等待行军
                and not player.has_status(Status.DEFENSIVE) # 不要让防御性的队友随意破墙
                and not player.has_status(Status.RELOADING) # 目前有弹药
                and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=1)
                ): # 上两回合也处于僵持状态

                # 触发的条件是一方隔墙，队友因为这两个人的僵持受到牵制
                #----------------------------------------------------

                # 僵持方先破墙，留好后路
                #----------------------
                action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_BRICK)
                if Signal.is_break(signal3):
                    continue

                if signal3 == Signal.READY_TO_PREPARE_FOR_BREAK_BRICK: # 下一步准备凿墙
                    returnActions[idx] = action3
                    hasTeamActions[idx] = True
                    continue # 至此决策完成，等待队友凿墙

                # elif signal3 == Signal.READY_TO_BREAK_BRICK:
                # 否则将受到破墙信号，开始判断是否符合破墙条件

                oppBattler = player.get_risky_enemy_battler() # 获得墙后敌人
                oppPlayer = Tank2Player(oppBattler)
                if oppPlayer.has_status(Status.ENCOUNT_ENEMY): # 发现敌人和队友相遇，立即破墙
                    returnActions[idx] = action3
                    hasTeamActions[idx] = True
                    continue # 至此完成单人决策


                playerIdx   = idx
                teammateIdx = 1 - idx
                teammate = player.teammate

                shouldBreakBrick = False

                # TODO:
                #   这种情况挺难遇到的，而且一旦遇到一般都为时过晚
                #   应该要模拟地图预测一下，提前开一炮
                #
                if (teammate.has_status(Status.WAIT_FOR_MARCHING) # 队友等待
                    # and self.has_status_in_previous_turns(teammate, Status.WAIT_FOR_MARCHING, turns=1)
                    and teammate.has_status(Status.PREVENT_BEING_KILLED)   # 队友是为了防止被杀
                    ):
                    teammateRiskyEnemyBattler = teammate.get_risky_enemy_battler()
                    playerRiskyEnemyBattler = player.get_risky_enemy_battler() # 墙后敌人
                    if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                        # 两者受到同一个敌人牵制，那么发动破墙信号
                        shouldBreakBrick = True

                elif ( teammate.has_status(Status.AGGRESSIVE)
                    or teammate.has_status(Status.STALEMENT)
                    ):
                    teammateAction = returnActions[ teammateIdx ] # 确保队友动作为移动
                    if (Action.is_move(teammateAction)
                        and teammate.has_status(Status.KEEP_ON_MARCHING) # 队友正在行军
                        ):
                        # 尝试模拟下一回合的队友状态，并让队友重新决策，查看他的状态
                        map_.simulate_one_action(teammate, teammateAction)
                        action4, _ = teammate.make_decision()
                        if (teammate.has_status(Status.WAIT_FOR_MARCHING)
                            and teammate.has_status(Status.PREVENT_BEING_KILLED)
                            ): # 这个时候队友被阻拦
                            teammateRiskyEnemyBattler = teammate.get_risky_enemy_battler()
                            playerRiskyEnemyBattler = player.get_risky_enemy_battler()
                            if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                shouldBreakBrick = True # 如果是因为对面墙的坦克在阻拦，那么马上破墙
                        map_.revert()


                if shouldBreakBrick:
                    returnActions[playerIdx] = action3
                    hasTeamActions[playerIdx] = True


        # 主动破墙策略
        #---------------------------------------
        # 如果可以主动破墙，且对方上一回合还在墙后面，这一回合离开了，那么主动破墙
        # 不管对方为什么离开，都不亏，假如对方下一回合回头，我方就攻过去，假如对方是赶去支援
        # 我方上前，然后等待一回合后会触发强攻信号
        #
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (Action.is_stay(action)
                and not player.has_status(Status.HAS_ENEMY_BEHIND_BRICK)
                and self.has_status_in_previous_turns(player, Status.HAS_ENEMY_BEHIND_BRICK, turns=1)
                and not player.has_status(Status.RELOADING) # 本回合可以射击
                ):
                action3, signal3 = player.make_decision(Signal.PREPARE_FOR_BREAK_BRICK)
                if Signal.is_break(signal3):
                    continue
                if signal3 == Signal.READY_TO_BREAK_BRICK: # 可以破墙，则选择破墙
                    returnActions[idx] = action3
                    hasTeamActions[idx] = True




        # TODO: 主动破墙之二打一
        #---------------------------
        # 如果遇到两个人隔着两个墙对着一个敌人的时候，就直接破墙
        #



        # 主动打破重叠的信号
        #-------------------
        # 1. 很多时候只有主动打破重叠，才能制造机会！
        #
        for idx, (player, action) in enumerate(zip(self.players, returnActions)):
            if (Action.is_stay(action)
                and player.has_status(Status.OVERLAP_WITH_ENEMY)  # 在等待敌人
                and not player.has_status(Status.RELOADING)       # 确认一下有炮弹
                and self.has_status_in_previous_turns(player, Status.OVERLAP_WITH_ENEMY, turns=3)
                ): # 数个回合里一直在等待

                action3, signal3 = player.make_decision(Signal.SUGGEST_TO_BREAK_OVERLAP)
                if Signal.is_break(signal3):
                    continue

                if signal3 == Signal.READY_TO_BREAK_OVERLAP:
                    returnActions[idx] = action3


        # 主动找重叠策略
        #-------------------
        # 如果当前为侵略性的，然后双方相邻，这个时候可以先后退一步
        # 然后下一步移动，尝试和对方重叠，这样有可能过掉对方



        action1, action2 = returnActions

        if action1 == Action.INVALID:
            action1 = Action.STAY
        if action2 == Action.INVALID:
            action2 = Action.STAY
        return [ action1, action2 ]

#{ END }#
