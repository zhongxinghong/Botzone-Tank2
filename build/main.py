# -*- coding: utf-8 -*-
# @Author:   Rabbit
# @Filename: main.py
# @Date:     2019-04-25 10:24:31
# @Description: Auto-built single-file Python script for Botzone/Tank2


# BEGIN const.py #

MAP_HEIGHT     = 9
MAP_WIDTH      = 9
SIDE_COUNT     = 2
TANKS_PER_SIDE = 2

GAME_STATUS_NOT_OVER = -2
GAME_STATUS_DRAW     = -1
GAME_STATUS_BLUE_WON = 0
GAME_STATUS_RED_WON  = 1

# END const.py #



# BEGIN stream.py #

class BotzoneIstream(object):

    def read(self):
        return input()


class BotzoneOstream(object):

    def write(self, data):
        print(data)

# END stream.py #



# BEGIN botzone.py #

import json
import sys


class Botzone(object):

    def __init__(self, long_running):
        self._longRunning = long_running
        self._data = None
        self._globalData = None
        self._requests = []  # 对方的决策
        self._responses = [] # 己方的决策


    def handle_input(self, stream):
        """
        解析输入信息

        Input:
            - stream   TextIOWrapper   输入流对象，必须实现 read 方法
        """
        inputJSON = json.loads(stream.read())

        self._requests   = inputJSON["requests"]
        self._responses  = inputJSON["responses"]
        self._data       = inputJSON.get("data", None)
        self._globalData = inputJSON.get("globaldata", None)

    def make_output(self, stream, response, debug, data, globaldata):
        """
        输出结果

        Input：
            - stream       TextIOWrapper   输出流对象，必须实现 write 方法
            - response     dict            Bot 此回合的输出信息
            - debug        str             调试信息，将被写入log，最大长度为1KB
            - data         dict            Bot 此回合的保存信息，将在下回合输入
            - globaldata   dict            Bot 的全局保存信息，将会在下回合输入，
                                             对局结束后也会保留，下次对局可以继续利用
        """
        stream.write(json.dumps({
            "response": response,
            "debug": debug,
            "data": data,
            "globaldata": globaldata,
            }))

        if not self._longRunning:
            sys.exit(0)



class Tank2Botzone(Botzone):

    def __init__(self, map, long_running=False):
        super().__init__(long_running)
        self._mySide = -1
        self._map = map


    @property
    def mySide(self):
        return self._mySide


    def _parse_field_points(self, binary):
        """
        解析 requests 中存在有某种类型 field 的坐标

        Input:
            - binary   list   某种类型 field 的 binary 标记
        Yield:
            - (x, y)   tuple(int, int)   这个坐标上存在该类型 field
        """
        _MAP_WIDTH = self._map.width
        for i in range(3):
            mask = 1
            for y in range(i * 3, i * 3 + 3):
                for x in range(_MAP_WIDTH):
                    if binary[i] & mask:
                        yield (x, y)
                    mask <<= 1

    def handle_input(self, stream=sys.stdin):

        super().handle_input(stream)

        header = self._requests.pop(0) # 此时 header 被去掉

        self._mySide = header["mySide"]

        for x, y in self._parse_field_points(header["brickfield"]):
            self._map.create_brick_field(x, y)

        for x, y in self._parse_field_points(header["steelfield"]):
            self._map.create_steel_field(x, y)

        for x, y in self._parse_field_points(header["waterfield"]):
            self._map.create_water_field(x, y)

        self._map.do_actions(self._mySide, self._responses, self._requests)


    def make_output(self, actions, stream=sys.stdout, **kwargs):
        debug = kwargs.get("debug", None)
        data = kwargs.get("data", None)
        globalData = kwargs.get("globaldata", None)
        super().make_output(stream, actions, debug, data, globalData)

# END botzone.py #



# BEGIN action.py #

class Action(object):

    DUMMY       = -3
    INVALID     = -2
    STAY        = -1
    MOVE_UP     = 0
    MOVE_RIGHT  = 1
    MOVE_DOWN   = 2
    MOVE_LEFT   = 3
    SHOOT_UP    = 4
    SHOOT_RIGHT = 5
    SHOOT_DOWN  = 6
    SHOOT_LEFT  = 7

    # 根据 action 的值判断移动方向和射击方向
    DIRECTION_OF_ACTION_X  = (  0, 1, 0, -1 )
    DIRECTION_OF_ACTION_Y  = ( -1, 0, 1,  0 )

    @staticmethod
    def is_move(action):
        """
        是否为移动行动
        """
        return 0 <= action <= 3

    @staticmethod
    def is_shoot(action):
        """
        是否为射击行动
        """
        return 4 <= action <= 7

    @staticmethod
    def is_opposite(action1, action2):
        """
        两个行动方向是否相对

        注： 此处不检查两个行为是否均与方向有关，即均处于 [0, 7] 范围内
        """
        return action1 % 4 == (action2 + 2) % 4

# END action.py #



# BEGIN field.py #

class Field(object):

    DUMMY = -1
    EMPTY = 0
    BASE  = 1
    BRICK = 2
    STEEL = 3
    WATER = 4
    TANK  = 5

    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.destroyed = False

    @property
    def coordinate(self):
        return (self.x, self.y)


class EmptyField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.EMPTY)


class BaseField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.BASE)


class BrickField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.BRICK)


class SteelField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.STEEL)


class WaterField(Field):

    def __init__(self, x, y):
        super().__init__(x, y, Field.WATER)


class TankField(Field):

    def __init__(self, x, y, side, id):
        super().__init__(x, y, Field.TANK)
        self._side = side
        self._id = id
        self.previousAction = Action.DUMMY

    @property
    def side(self):
        return self._side

    @property
    def id(self):
        return self._id

# END field.py #



# BEGIN map_.py #

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

# END map_.py #



# BEGIN strategy.py #



# END strategy.py #



# BEGIN main.py #

import random

if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_)

    istream = BotzoneIstream()
    ostream = BotzoneOstream()

    while True:

        terminal.handle_input(stream=istream)

        side = terminal.mySide
        tanks = map_.tanks[side]

        actions = []
        for tank in tanks:
            availableActions = [
                action for action in range(Action.STAY, Action.SHOOT_LEFT + 1)
                    if map_.is_valid_action(tank, action)
            ]
            actions.append(random.choice(availableActions))

        terminal.make_output(actions, stream=ostream)

# END main.py #



