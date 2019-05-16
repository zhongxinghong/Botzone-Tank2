# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-29 23:02:34
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-17 06:47:45
"""
状况评估
"""

__all__ = [

    "evaluate_aggressive",
    "estimate_route_similarity",
    "estimate_enemy_effect_on_route",

    ]

from ..global_ import np
from ..utils import debug_print, debug_pprint
from ..action import Action
from ..field import BaseField, BrickField, SteelField, TankField, WaterField, EmptyField
from .utils import get_manhattan_distance
from .status import Status
from .search import get_searching_directions

#{ BEGIN }#

def evaluate_aggressive(battler, oppBattler):
    """
    根据敌我两架坦克的攻击线路长短，衡量当前侵略性

    Input:
        - battler      BattleTank
        - oppBattler   BattleTank

    Return:
        [status]
        - Status.AGGRESSIVE   我方处于攻击状态
        - Status.DEFENSIVE    我方处于防御状态
        - Status.STALEMENT    双方处于僵持状态
    """
    myRoute = battler.get_shortest_attacking_route()
    oppRoute = oppBattler.get_shortest_attacking_route()

    # 可能会遇到这种糟糕的情况，队友挡住了去路 5cdde41fd2337e01c79f1284
    #--------------------------
    if myRoute.is_not_found() or oppRoute.is_not_found():
        return Status.AGGRESSIVE # 应该可以认为是侵略吧


    # assert not myRoute.is_not_found() and not oppRoute.is_not_found(), "route not found"
    leadingLength = oppRoute.length - myRoute.length

    # debug_print(battler, oppBattler, "leading:", leadingLength)

    if battler.is_in_enemy_site(): # 在敌方半边地图，更倾向于不防御

        if leadingLength >= 1:
            return Status.AGGRESSIVE
        elif leadingLength < -2:
            return Status.DEFENSIVE
        else:
            return Status.STALEMENT

    else: # 在我方半边地盘，会增加防御的可能性

        if leadingLength >= 1:
            return Status.AGGRESSIVE
        elif leadingLength <= -1:
            return Status.DEFENSIVE
        else:
            return Status.STALEMENT


def estimate_route_similarity(route1, route2):
    """
    评估两条路线的相似度
    一般用于判断选择某条路线是否可以和敌人相遇

    实现思路：
    --------------
    首先找出两者中最短的一条路径，对于其上每一个点，在另一条路上寻找与之距离最短（曼哈顿距离即可）
    的点，并将这两个点之间的距离作为总距离的一个部分，每个分距离和相应点的权重的加权平均值即为总距离

    最后的估值为 总距离除以最短路线的坐标点数的均值 的倒数
    值越接近 1 表示越相近，值越接近 0 表示越不相近

    根据实际情景的需要，我们将较长路劲多出来的那些点忽略 ...


    TODO:
    -------------
    1. 如何考虑坐标权重
    2. 如何考虑长路径中多出来的那些点

    """
    route1 = [ (node.x, node.y, node.weight) for node in route1 ]
    route2 = [ (node.x, node.y, node.weight) for node in route2 ]

    if len(route1) > len(route2): # 确保 route1 坐标数不超过 route2
        route1, route2 = route2, route1

    total = 0
    for x1, y1, weight in route1:
        d = np.min([ get_manhattan_distance(x1, y1, x2, y2) for x2, y2, _ in route2 ])
        total += d * weight

    return 1 / ( total / len(route1) + 1 )


def estimate_enemy_effect_on_route(route, player):
    """
    衡量敌人对我方所选的进攻路线的影响程度
    ----------------------------------------
    敌人在进攻路线两侧，可能会阻碍进攻，也就是增加了相应路线进攻的回合数，
    因此敌人的影响可以量化为相应路线长度的增加量。

    将理论路线长度与敌人的影响所导致的长度增加量相加，所得的估值可以认为是
    考虑了敌人影响后的真实路线长度，可以将这个真实路线长度对所选路线进行重新
    排序，从而选出距离短，且受敌人影响最小的攻击路线


    如何估计敌人影响？
    ------------------
    收集敌人当前所在位置所能影响到（近乎可认为是能射击到）的坐标。为了确保更加接近真实的情况，
    再假设敌人当前回合能射击，模拟敌人所有可以执行的动作（包括移动和射击，考虑射击是因为有可能可以
    摧毁一些土墙），之后同法收集敌人所能影响到的坐标。将这一坐标集所对应的区域视为受到敌人影响的区域。

    随后统计当前路径与该坐标集的重叠程度（路径上的坐标出现在该坐标集内的，可视为重叠。这种路径节点的
    数量越多，重叠程度越大），并认为这一重叠程度与敌人的影响程度正相关，也就是重叠的坐标点数与
    路径长度的增长量正相关，从而实现量化估计。

    特别的，如果敌人出现在攻击路线上，会造成较大的路线长度增加，有时甚至可以视为此路不通。


    TODO:
    ---------
    这种简单的静态分析策略可能存在对某些具体情况估计不到位的问题。当我方坦克沿着这条路线走到需要和
    敌人正面交锋的位置时，有的时候可以通过闪避直接躲开，这种情况的影响可能比较小。而有的情况下是无法躲开的，
    我方坦克只能选择往回闪避，这就相当于判定了这条路为死路 5cd24632a51e681f0e912613
    （然而事实上情况还可以更加复杂，因为实际进攻的时候，有可能会采用一些特殊的策略，让这条路转化为活路，
    例如预先打掉与我距离为 2 的墙）。
    而在静态分析中，这些具体的差别可能无法区分，因此和更加真实合理的估计间可能存在着一定的差距。

    但是采用动态分析可能不是一件很现实的事情，因为需要不断地模拟移动和模拟决策，一方面会造成算法过于
    耗时，一方面也有可能会引入各种混乱（实现无差异地在多回合模拟移动和模拟决策间回滚，并且确保面向真实情况
    决策的代码也能适用于模拟决策的情况，这将会是一个浩大的工程）。


    Input:
        - route    Route         待评估的路线
        - player   Tank2Player   将会采用这条路线的玩家对象


    """
    map_ = player._map  # 通过玩家对象引入 map 全局对象

    LENGTH_INCREMENT_OF_ENEMY_INFLUENCED = 1   # 受到敌人射击影响所导致的路线长度增量
    LENGTH_INCREMENT_OF_ENEMY_BLOCKING   = 10  # 敌人位于路线上所导致的路线长度增量

    enemyInfluencedPoints = set()  # 受敌人影响的坐标集
    enemyBlockingPoints   = set()  # 敌人阻塞的坐标集

    for oppBattler in [ oppPlayer.battler for oppPlayer in player.opponents ]:
        if oppBattler.destroyed:
            continue
        with map_.simulate_one_action(oppBattler, Action.STAY): # 刷新射击回合
            for action in oppBattler.get_all_valid_actions(): # 包含了原地停止
                with map_.simulate_one_action(oppBattler, action):
                    with map_.simulate_one_action(oppBattler, Action.STAY): # 同理刷新冷却

                        enemyBlockingPoints.add( oppBattler.xy ) # blocking
                        enemyInfluencedPoints.add( oppBattler.xy ) # 先加入敌人当前坐标

                        for dx, dy in get_searching_directions(*oppBattler.xy):
                            x, y = oppBattler.xy
                            while True:
                                x += dx
                                y += dy
                                if not map_.in_map(x, y):
                                    break
                                fields = map_[x, y]
                                if len(fields) == 0:
                                    pass
                                elif len(fields) > 1: # 两个以上敌人，不划入影响范围，并直接结束
                                    break
                                else:
                                    field = fields[0]
                                    if isinstance(field, EmptyField):
                                        pass
                                    elif isinstance(field, WaterField):
                                        continue # 水路可以认为不影响
                                    #elif isinstance(field, (BaseField, BrickField, SteelField, TankField) ):
                                    else:
                                        break #　block 类型，不划入影响范围，并直接结束

                                enemyInfluencedPoints.add( (x, y) ) # 以 pass 结尾的分支最后到达这里


    realLength = route.length # 初始为路线长度

    for node in route:
        xy = node.xy
        if xy in enemyInfluencedPoints:
            if node.weight > 0: # 射击的过渡点 weight == 0 它，它实际上不受敌人射击的影响
                realLength += LENGTH_INCREMENT_OF_ENEMY_INFLUENCED
        if xy in enemyBlockingPoints:
            # 敌人阻塞，可以影响射击点，因此同等对待
            realLength += LENGTH_INCREMENT_OF_ENEMY_BLOCKING

    return realLength


#{ END }#