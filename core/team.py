# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-30 01:01:30
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 14:03:50
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
from .field import TankField
from .strategy.status import Status
from .strategy.signal import Signal
from .decision.abstract import DecisionMaker
from .player import Tank2Player

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
            try:
                previousStatus = allStatus[i][player.id]
            except IndexError: # 可能 allStatus 为空
                return False
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
        return self._previousActions[player.id][-back]


    def _make_decision(self):
        """
        团队决策

        Return:
            - actions    [int, int]    0, 1 号玩家的决策
        """
        map_     = self._map
        player1  = self._player1
        player2  = self._player2
        battler1 = player1.battler
        battler2 = player2.battler


        # 假装先让对方以自己的想法决策
        #-------------------------------
        # 分析对方的行为，可以对下一步的行为作出指导
        #
        for oppPlayer in self._opponentTeam.players:
            oppPlayer.make_decision()


        # 保存玩家的最终决策结果
        action1 = action2 = Tank2Player.UNHANDLED_RESULT
        signal1 = signal2 = Signal.NONE

        # 中级变量
        action3 = action4 = Tank2Player.UNHANDLED_RESULT
        signal3 = signal4 = Signal.NONE


        # 我方玩家单独决策
        #------------------------------
        # 了解个人真实想法
        #

        action1, _ = player1.make_decision()
        action2, _ = player2.make_decision()

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


        # 打破队友重叠的信号
        #------------------
        # 己方两个坦克重叠在一起这种事情实在是太愚蠢了 ...
        #
        if player1.tank.xy == player2.tank.xy:

            if len([ action for action in returnActions if Action.is_move(action) ]) == 1:
                pass # 一人移动一人非移动，那么是合理的
            elif (all( Action.is_move(action) for action in returnActions )
                and returnActions[0] != returnActions[1]
                ): # 两人均为移动，但是两人的移动方向不一样，这样也是可以的
                pass
            elif all(hasTeamActions): # 两者都拥有强制命令
                pass
            else:
                # 两个队员可以认为是一样的，因此任意选择一个就好
                if hasTeamActions[0]:
                    player, idx = (player2, 1)
                else:
                    player, idx = (player1, 0)

                action3, signal3 = player.make_decision(Signal.SHOULD_LEAVE_TEAMMATE)
                if signal3 == Signal.READY_TO_LEAVE_TEAMMATE:
                    returnActions[idx]  = action3
                    hasTeamActions[idx] = True


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
                #and not player.has_status(Status.DEFENSIVE) # 不要让防御性的队友随意破墙
                and not player.has_status(Status.RELOADING) # 目前有弹药
                # and self.has_status_in_previous_turns(player, Status.WAIT_FOR_MARCHING, turns=1) # 改成一有机会就先留后路
                ):

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

                ''' 这个两个触发已经不再需要了 5ce217e8d2337e01c7a3790c

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
                    teammateAction = returnActions[ teammateIdx ]
                    if (Action.is_move(teammateAction) # 确保队友动作为移动
                        and teammate.has_status(Status.KEEP_ON_MARCHING) # 队友正在行军
                        ):
                        # 尝试模拟下一回合的队友状态，并让队友重新决策，查看他的状态
                        with map_.simulate_one_action(teammate, teammateAction):
                            action4, _ = teammate.make_decision()
                            if (teammate.has_status(Status.WAIT_FOR_MARCHING)
                                and teammate.has_status(Status.PREVENT_BEING_KILLED)
                                ): # 这个时候队友被阻拦
                                teammateRiskyEnemyBattler = teammate.get_risky_enemy_battler()
                                playerRiskyEnemyBattler = player.get_risky_enemy_battler()
                                if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                                    shouldBreakBrick = True # 如果是因为对面墙的坦克在阻拦，那么马上破墙'''

                #
                # 如果遇到对手准备和队友对射 5cd364e4a51e681f0e921e7a
                # 那么考虑直接破墙
                #
                # 敌方当前回合应该必定会还击，否则就失去了防御的意义
                # 于是，随后就会遇到二对一且三方均没有炮弹
                # 如果对方下回合不走，那么二打一直接干掉
                # 如果对方下回合移动，那么攻击的队友就解除了威胁，可以继续前进
                #
                if (not teammate.has_status(Status.DEFENSIVE)
                    and teammate.has_status(Status.ENCOUNT_ENEMY)
                    and teammate.has_status(Status.READY_TO_FIGHT_BACK)
                    ):
                    teammateRiskyEnemyBattler = teammate.get_risky_enemy_battler()
                    playerRiskyEnemyBattler = player.get_risky_enemy_battler()
                    if teammateRiskyEnemyBattler is playerRiskyEnemyBattler:
                        shouldBreakBrick = True

                if shouldBreakBrick:
                    returnActions[playerIdx] = action3
                    hasTeamActions[playerIdx] = True


        # 主动破墙策略
        #---------------------------------------
        # 如果可以主动破墙，且对方上一回合还在墙后面，这一回合离开了，那么主动破墙
        # 不管对方为什么离开，都不亏，假如对方下一回合回头，我方就攻过去，假如对方是赶去支援
        # 我方上前，然后等待一回合后会触发强攻信号
        #
        # 这个策略已经不再适用了！ 5ce01b75d2337e01c7a11d4d
        # 容易导致被敌人突击
        #
        '''for idx, (player, action) in enumerate(zip(self.players, returnActions)):
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
                    hasTeamActions[idx] = True'''


        # TODO: 主动破墙之二打一
        #---------------------------
        # 如果遇到两个人隔着两个墙对着一个敌人的时候，就直接破墙
        #


        # 主动找重叠策略
        #-------------------
        # 如果当前为侵略性的，然后双方相邻，这个时候可以先后退一步
        # 然后下一步移动，尝试和对方重叠，这样有可能过掉对方



        '''#
        # 如果两架坦克同时射向同一个块，最终两个炮弹将会浪费一个
        # 在这种情况下不如让一方改为停止
        #
        # 对于重叠拆基地的情况，往往有奇效
        #
        #
        # 不过要注意判断被摧毁的块是什么，不能是坦克，因为敌方坦克可以移走
        # 那么这时我方两个坦克对炮，如果一个射击一个不射击，就会打到自己人
        #
        action1, action2 = returnActions
        if Action.is_shoot(action1) and Action.is_shoot(action2):
            destroyedFields1 = battler1.get_destroyed_fields_if_shoot(action1)
            destroyedFields2 = battler2.get_destroyed_fields_if_shoot(action2)
            if destroyedFields1 == destroyedFields2:
                for field in destroyedFields1:
                    if isinstance(field, TankField):
                        break # 这种情况仍然保持两人同时射击
                else: # 没有 tank
                    returnActions[0]  = Action.STAY # 仍选一个
                    hasTeamActions[0] = True

        #
        # 判断是否出现队友恰好打掉准备移动的队友的情况
        #
        action1, action2 = returnActions
        _mayShouldForcedStop = False
        if Action.is_shoot(action1) and Action.is_move(action2):
            shootAction = action1
            shootPlayer = player1
            moveAction  = action2
            movePlayer  = player2
            _mayShouldForcedStop = True
        elif Action.is_move(action1) and Action.is_shoot(action2):
            shootAction = action2
            shootPlayer = player2
            moveAction  = action1
            movePlayer  = player1
            _mayShouldForcedStop = True

        if _mayShouldForcedStop:
            moveBattler = movePlayer.battler
            shootBattler = shootPlayer.battler
            _shouldForcedStop = False
            with map_.simulate_one_action(moveBattler, moveAction):
                with map_.simulate_one_action(shootBattler, shootAction):
                    if moveBattler.destroyed: # 刚好把队友打死 ...
                        _shouldForcedStop = True

            if _shouldForcedStop:
                #
                # TODO:
                #   如何决策？
                #   改动射击和决策都有可能很危险
                #

                #
                # 这里先做一个特殊情况，那就是重叠攻击基地，这种情况将移动的队友视为不移动
                #
                # TODO:
                #   好吧，这种情况和主动和队友打破重叠的行为是相斥的 ...
                #
                if (moveBattler.xy == shootBattler.xy
                    and moveBattler.is_face_to_enemy_base(ignore_brick=False)
                    and shootBattler.is_face_to_enemy_base(ignore_brick=False)
                    ):
                    returnActions[movePlayer.id] = Action.STAY
                    hasTeamActions[movePlayer.id] = True'''



        action1, action2 = returnActions
        # 如果存在玩家没有处理，那么
        if not player1.is_handled(action1):
            action1 = Action.STAY
        if not player2.is_handled(action2):
            action2 = Action.STAY

        return [ action1, action2 ]

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
