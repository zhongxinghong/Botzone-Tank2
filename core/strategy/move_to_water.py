# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-27 16:22:47
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-28 06:52:38
"""
[TEST] 移动向距离自己最近的水域

Step：
1. 找到最近的水面（欧氏距离）
2. 通过 BFS 查找最短路径，由此确定下一个理想的移动行为
3. 判断是否可以移动，不能移动则尝试射击
4. 判断是否可以射击，不能射击则当回合停止
"""

__all__ = [

    "MoveToWaterStrategy",

    ]

from ..const import DEBUG_MODE
from ..global_ import np, pprint
from ..action import Action
from ..field import Field, WaterField
from .abstract import SingleTankStrategy
from ._utils import find_shortest_route

#{ BEGIN }#

class MoveToWaterStrategy(SingleTankStrategy):

    def __init__(self, tank, map, water_points=None):
        """
        可以传入 water_points 的坐标，避免多次计算
        """
        super().__init__(tank, map)
        self._waterPoints = water_points


    @staticmethod
    def find_water_points(map):
        return np.argwhere(map.matrix_T == Field.WATER) # 转置为 xy 矩阵


    def make_decision(self):

        if self._waterPoints is None:
            self._waterPoints = self.find_water_points(self._map)

        tank        = self._tank
        map_        = self._map
        matrix_T    = map_.matrix_T
        waterPoints = self._waterPoints

        _dx = Action.DIRECTION_OF_ACTION_X
        _dy = Action.DIRECTION_OF_ACTION_Y


        xy = np.array( tank.xy )
        _idx = np.square( xy - waterPoints ).sum(axis=1).argmin()
        x2, y2 = nearestWaterPoint = waterPoints[_idx]

        route = find_shortest_route(
                    tank.xy,
                    nearestWaterPoint,
                    matrix_T,
                    cannot_reach_type=[Field.STEEL] ) # 水域允许到达

        if DEBUG_MODE:
            map_.print_out()
            pprint(self._map.matrix)
            print("")
            pprint(route)

        x1, y1 = tank.xy
        if len(route) == 0:
            raise Exception("can't reach (%s, %s)" % (x2, y2) )

        if len(route) == 1: # 说明 start 和 end 相同
            x3, y3 = nextPoint = route[0] # 返回 start/end
        else:
            x3, y3 = nextPoint = route[1] # 跳过 start

        action = Action.get_action(x1, y1, x3, y3) # 必定是 move-action

        if not map_.is_valid_move_action(tank, action): # 墙或水
            x, y = tank.xy
            x += _dx[action]
            y += _dy[action]
            fields = map_[x, y]
            assert len(fields) > 0, "except WATER or BRICK in (%s, %s)" % (x, y)
            field = fields[0]
            action += 4 # 尝试射击
            if not isinstance(field, WaterField): # 说明是墙
                pass # 射击一定成功，因为若上回合射击，这回合必定不会碰到墙
            else: # 是水面
                if map_.is_valid_shoot_action(tank, action): # 判断上回合是否射击
                    pass
                else: # 射击行为也不合法
                    action = Action.STAY # 如果游戏正常，则会停下，否则一开始会认为是合法，并继续移动

        return action

#{ END }#