# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-29 23:02:34
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-28 16:10:43
"""
状况评估
"""

__all__ = [

    "evaluate_aggressive",
    "estimate_route_similarity",
    "estimate_enemy_effect_on_route",
    "estimate_route_blocking",

    ]

from ..global_ import np
from ..utils import debug_print, debug_pprint
from ..action import Action
from ..field import BaseField, BrickField, SteelField, TankField, WaterField, EmptyField
from .utils import get_manhattan_distance
from .status import Status
from .search import get_searching_directions

#{ BEGIN }#

def evaluate_aggressive(battler, oppBattler, strict=False, allow_withdraw=True):
    """
    根据敌我两架坦克的攻击线路长短，衡量当前侵略性

    Input:
        - battler           BattleTank
        - oppBattler        BattleTank
        - strict            bool   是否严格依据路线长度和两方基地位置进行评估
                                   如果为 False ，则还会考虑其他的因素
        - allow_withdraw    bool   是否允许撤退

    Return:
        [status]
        - Status.AGGRESSIVE   我方处于攻击状态
        - Status.DEFENSIVE    我方处于防御状态
        - Status.STALEMENT    双方处于僵持状态
        - Status.WITHDRAW     我方处于撤退状态
    """
    map_ = battler._map
    BattleTank = type(battler)

    myRoute = battler.get_shortest_attacking_route()
    oppRoute = oppBattler.get_shortest_attacking_route()

    # 可能会遇到这种糟糕的情况，队友挡住了去路 5cdde41fd2337e01c79f1284
    #--------------------------
    if myRoute.is_not_found() or oppRoute.is_not_found():
        return Status.AGGRESSIVE # 应该可以认为是侵略吧


    # assert not myRoute.is_not_found() and not oppRoute.is_not_found(), "route not found"
    leadingLength = oppRoute.length - myRoute.length

    #debug_print(battler, oppBattler, "leading:", leadingLength)

    if battler.is_in_enemy_site(): # 在敌方半边地图，更倾向于不防御

        if leadingLength >= 1:
            status = Status.AGGRESSIVE
        elif leadingLength < -3:
            status = Status.DEFENSIVE
        else:
            status = Status.STALEMENT

    else: # 在我方半边地盘，会增加防御的可能性

        if leadingLength >= 1:
            status = Status.AGGRESSIVE # [1, +)
        elif -1 <= leadingLength < 1:
            status = Status.STALEMENT  # [-1, 1)
        elif -2 <= leadingLength < -1:
            status = Status.DEFENSIVE  # [-2, -1)
        else:
            if allow_withdraw and battler.is_in_our_site(include_midline=True): # 包含中线，放松一点条件
                status = Status.WITHDRAW   # (-, -2)
            else:
                status = Status.DEFENSIVE # 否则不要撤退？

    if strict: # 严格模式直接返回评估状态
        return status

    #
    # 撤退性状态直接返回
    #
    if status == Status.WITHDRAW:
        return status

    #
    # 尽可能用攻击性策略！
    #
    # 还要判断对方的攻击路线是否可能会被我方队员阻拦
    # 否则就过度防御了 5ce69a15d2337e01c7a90646
    #
    if status != Status.AGGRESSIVE:
        map_ = battler._map
        tank = battler.tank
        teammate = None
        for _tank in map_.tanks[tank.side]:
            if _tank is not tank:
                teammate = _tank
                break

        if not teammate.destroyed:
            teammateBattler = BattleTank(teammate)
            for action in teammateBattler.get_all_valid_move_actions() + [ Action.STAY ]:
                with map_.simulate_one_action(teammateBattler, action):
                    if teammateBattler.xy in oppRoute:  # 此时视为侵略模式
                        return Status.AGGRESSIVE

    return status


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


def estimate_route_blocking(route):
    """
    评估路线上 block 类型块的数量
    ----------------------------
    被用于撤退路线的评估

    撤退行为发生在己方基地，不宜过度攻击墙，否则可能会削弱基地的防御性


    实现方法
    -------------
    让 block 类型的块的权重增加，这样就可以让 block 更多的路线的长度增加


    TODO:
        是否对含有相同 block 的路线上的 block 进行进一步的评估？也就是认为基地外围的 block 的权重更高？

    """
    x2, y2 = route.end

    LENGTH_INCREMENT_OF_BLOCK           = 1  # 遇到墙，权重加 1
    LENGTH_INCREMENT_OF_INNERMOST_BLOCK = 2  # 遇到最内层的墙，权重加 2

    realLength = route.length

    for node in route:
        x1, y1 = node.xy
        if node.weight == 2: # 权重为 2 的块一定是 block 类型
            if np.abs(x1 - x2) <= 1 and np.abs(y1 - y2) <= 1: # 位于 end 的外围
                realLength += LENGTH_INCREMENT_OF_INNERMOST_BLOCK
            else:
                realLength += LENGTH_INCREMENT_OF_BLOCK

    return realLength

#{ END }#