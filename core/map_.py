# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 23:48:49
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 10:06:52

__all__ = [

    "Tank2Map",

    ]

from .field import (

    Field,
    EmptyField,
    BaseField,
    BrickField,
    SteelField,
    WaterField,
    TankField,

)

from .action import Action

from .const import (

    SIDE_COUNT,
    TANKS_PER_SIDE,

    GAME_STATUS_NOT_OVER,
    GAME_STATUS_DRAW,
    GAME_STATUS_BLUE_WON,
    GAME_STATUS_RED_WON,

)


#{ BEGIN }#

class Map(object):

    def __init__(self, width, height):
        self._width = width
        self._height = height

        self._content = [
            [[] for x in range(width)] for y in range(height)
        ]

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height


class Tank2Map(Map):

    def __init__(self, width, height):
        super().__init__(width, height)
        self._tanks = [ [ None for _ in range(TANKS_PER_SIDE) ] for __ in range(SIDE_COUNT) ]
        self._bases = [ None for _ in range(SIDE_COUNT) ]
        self._init_bases()
        self._init_tanks()


    @property
    def tanks(self):
        return self._tanks


    def _init_bases(self):
        """
        初始化基地和基地前的钢墙
        """
        assert self._width % 2 == 1, "Map width must be odd"
        xc = self._width // 2 # x-center
        y1 = 0
        y2 = self._height - 1

        basePoints = [
            (xc, y1), # side 1 蓝方
            (xc, y2), # side 2 红方
        ]
        for side, (x, y) in enumerate(basePoints):
            base = self.create_base_field(x, y)
            self._bases[side] = base

    def _init_tanks(self):
        """
        初始化坦克
        """
        x1, x2 = (2, 6)
        y1, y2 = (0, self._height-1)
        tankPoints = [
            [ (x1, y1), (x2, y1) ], # side 1 蓝方  左 0 右 1
            [ (x2, y2), (x1, y2) ], # side 2 红方  左 1 右 0
        ]
        for side, points in enumerate(tankPoints):
            tanks = self._tanks[side]
            for idx, (x, y) in enumerate(points):
                tank = self.create_tank_field(x, y, side, idx)
                tanks[idx] = tank

    def reset(self):
        width = self._width
        height = self._height
        self.__init__(width, height)


    def insert_field(self, field):
        x, y = field.coordinate
        self._content[y][x].append(field)
        field.destroyed = False

    def remove_field(self, field):
        x, y = field.coordinate
        self._content[y][x].remove(field)
        field.destroyed = True

    def create_empty_field(self, x, y):
        field = EmptyField(x, y)
        self.insert_field(field)
        return field

    def create_base_field(self, x, y):
        field = BaseField(x, y)
        self.insert_field(field)
        return field

    def create_brick_field(self, x, y):
        field = BrickField(x, y)
        self.insert_field(field)
        return field

    def create_steel_field(self, x, y):
        field = SteelField(x, y)
        self.insert_field(field)
        return field

    def create_water_field(self, x, y):
        field = WaterField(x, y)
        self.insert_field(field)
        return field

    def create_tank_field(self, x, y, side, id):
        field = TankField(x, y, side, id)
        self.insert_field(field)
        return field


    def in_map(self, x, y):
        """
        判断 (x, y) 坐标是否位于地图内
        """
        return 0 <= x < self._width and 0 <= y < self._height


    def is_valid_action(self, tank, action):
        if action == Action.INVALID:
            return False
        elif Action.is_shoot(action) and Action.is_shoot(tank.previousAction): # 连续两回合射击
            return False
        elif action == Action.STAY or Action.is_shoot(action):
            return True
        elif Action.is_move(action):
            x, y = tank.coordinate
            _dx = Action.DIRECTION_OF_ACTION_X
            _dy = Action.DIRECTION_OF_ACTION_Y
            x += _dx[action]
            y += _dy[action]
            if not self.in_map(x, y):
                return False
            fields = self._content[y][x]
            if len(fields) == 0:
                return True
            elif len(fields) == 1:
                _type = fields[0].type
                if _type == Field.EMPTY or _type == Field.DUMMY:
                    return True
            return False
        else: # 未知的行为？
            return False


    def do_actions(self, my_side, my_actions, opposite_actions):
        """
        在地图上执行两方的行为
        """
        assert len(my_actions) ==  len(opposite_actions)

        _currentTurn = 0

        for aMyActions, anOppositeActions in zip(my_actions, opposite_actions):

            _currentTurn += 1
            #print("Current Turn: %s" % _currentTurn)
            #self.print_out()
            #from pprint import pprint
            #pprint(self.to_type_matrix())
            #print()

            _actions = [ None for _ in range(SIDE_COUNT) ]

            mySide  = my_side
            oppSide = 1 - my_side

            _actions[mySide]  = aMyActions
            _actions[oppSide] = anOppositeActions

            # 检查 actions 合理性
            for tanks in self._tanks:
                for tank in tanks:
                    action = _actions[tank.side][tank.id]
                    if not self.is_valid_action(tank, action):
                        print(tank.type, tank.id, action)
                        self.print_out()
                        raise Exception("Invalid action")

            _dx = Action.DIRECTION_OF_ACTION_X
            _dy = Action.DIRECTION_OF_ACTION_Y

            # 处理坦克移动
            for tanks in self._tanks:
                for tank in tanks:
                    action = _actions[tank.side][tank.id]
                    if ( not tank.destroyed
                         and Action.is_move(action)
                        ):
                        tank.previousAction = action # 缓存本次移动行动
                        self.remove_field(tank)
                        tank.x += _dx[action]
                        tank.y += _dy[action]
                        self.insert_field(tank)

            fieldToBeDestroyed = set()

            for tanks in self._tanks:
                for tank in tanks:

                    action = _actions[tank.side][tank.id]

                    if not tank.destroyed and Action.is_shoot(action):
                        tank.previousAction = action # 缓存本次射击行动

                        x, y = tank.coordinate
                        action %= 4 # 使之与 dx, dy 的 idx 对应

                        hasMultiTankWithMe = ( len( self._content[y][x] ) > 1 )

                        while True:
                            # 查找该行/列上是否有可以被摧毁的对象
                            x += _dx[action]
                            y += _dy[action]
                            if not self.in_map(x, y):
                                break
                            currentFields = self._content[y][x]

                            if len(currentFields) > 0:

                                if currentFields == 1: # 如果 > 1 则必定都是坦克
                                    field = currentFields[0]

                                    # 水路判断
                                    if isinstance(field, WaterField):
                                        continue # 忽视水路

                                    # 对射判断
                                    if ( not hasMultiTankWithMe
                                         and isinstance(field, TankField)
                                        ): # 此时两方所在格子均都只有一架坦克
                                        oppTank = field
                                        oppAction = _actions[oppTank.side][oppTank.id]
                                        if ( Action.is_shoot(oppAction)
                                             and Action.is_opposite(action, oppAction)
                                            ):
                                            break # 对射抵消

                                fieldToBeDestroyed.update(currentFields)
                                break # 摧毁了第一个遇到的 field

            for field in fieldToBeDestroyed:
                if not isinstance(field, SteelField):
                    self.remove_field(field)


    def get_game_result(self):

        failed = [ False for _ in range(SIDE_COUNT) ] # 0 蓝方 1 红方

        for side in range(SIDE_COUNT):

            # 坦克全部被消灭
            tanks = self._tanks[side]
            if all(tank.destroyed for tank in tanks):
                failed[side] = True

            # 基地被摧毁
            baes = self._bases[base]
            if base.destroyed:
                failed[side] = True

        if failed[0] and failed[1]:
            return GAME_STATUS_DRAW
        elif not failed[0] and failed[1]:
            return GAME_STATUS_BLUE_WON
        elif failed[0] and not failed[1]:
            return GAME_STATUS_RED_WON
        else:
            return GAME_STATUS_NOT_OVER


    def to_type_matrix(self):
        """
        转化成以 field.type 值表示的地图矩阵

        Return：
            - matrix   [[int]]   二维的 type 值矩阵
        """
        matrix = [ [ Field.DUMMY for x in range(self._width) ] for y in range(self._height) ]

        for y in range(self._height):
            for x in range(self._width):
                fields = self._content[y][x]
                if len(fields) == 0:
                    matrix[y][x] = Field.EMPTY
                elif len(fields) > 2:
                    matrix[y][x] = Field.TANK # 重合视为一个坦克
                else:
                    matrix[y][x] = fields[0].type

        return matrix

    def print_out(self):

        EMPTY_SYMBOL      = "　"
        BASE_SYMBOL       = "基"
        BRICK_SYMBOL      = "土"
        STEEL_SYMBOL      = "钢"
        WATER_SYMBOL      = "水"
        BLUE_TANK_SYMBOL  = "蓝"
        RED_TANK_SYMBOL   = "红"
        MULTI_TANK_SYMBOL = "重"
        UNEXPECTED_SYMBOL = "？"

        SPACE = "　"
        CUT_OFF_RULE = "＝" * (self._width * 2 - 1)

        from functools import partial
        print_inline = partial(print, end=SPACE)

        print("\n%s\n" % CUT_OFF_RULE)
        for y in range(self._height):
            for x in range(self._width):
                fields = self._content[y][x]
                if len(fields) == 0:
                    print_inline(EMPTY_SYMBOL)
                elif len(fields) > 1:
                    print_inline(MULTI_TANK_SYMBOL)
                elif len(fields) == 1:
                    field = fields[0]
                    if isinstance(field, EmptyField):
                        print_inline(EMPTY_SYMBOL)
                    elif isinstance(field, BaseField):
                        print_inline(BASE_SYMBOL)
                    elif isinstance(field, BrickField):
                        print_inline(BRICK_SYMBOL)
                    elif isinstance(field, SteelField):
                        print_inline(STEEL_SYMBOL)
                    elif isinstance(field, WaterField):
                        print_inline(WATER_SYMBOL)
                    elif isinstance(field, TankField):
                        tank = field
                        if tank.side == 0:
                            print_inline(BLUE_TANK_SYMBOL)
                        elif tank.side == 1:
                            print_inline(RED_TANK_SYMBOL)
                        else:
                            print_inline(UNEXPECTED_SYMBOL)
                    else:
                        print_inline(UNEXPECTED_SYMBOL)
                else:
                    print_inline(UNEXPECTED_SYMBOL)
            print("\n")
        print("%s\n" % CUT_OFF_RULE)

#{ END }#