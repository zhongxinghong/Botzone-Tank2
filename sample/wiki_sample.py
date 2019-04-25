# Tank 游戏样例程序
# 随机策略
# 作者：zhouhy
# https://www.botzone.org.cn/games/Tank
import json
import sys
import random
from typing import List

FIELD_HEIGHT = 9
FIELD_WIDTH = 9
SIDE_COUNT = 2
TANK_PER_SIDE = 2

dx = [ 0, 1, 0, -1 ]
dy = [ -1, 0, 1, 0 ]

class FieldItemType():
    Nil = 0
    Brick = 1
    Steel = 2
    Base = 3
    Tank = 4

class Action():
    Invalid = -2
    Stay = -1
    Up = 0
    Right = 1
    Down = 2
    Left = 3
    UpShoot = 4
    RightShoot = 5
    DownShoot = 6
    LeftShoot = 7

class WhoWins():
    NotFinished = -2
    Draw = -1
    Blue = 0
    Red = 1

class FieldObject:
    def __init__(self, x: int, y: int, itemType: FieldItemType):
        self.x = x
        self.y = y
        self.itemType = itemType
        self.destroyed = False

class Base(FieldObject):
    def __init__(self, side: int):
        super().__init__(4, side * 8, FieldItemType.Base)
        self.side = side

class Tank(FieldObject):
    def __init__(self, side: int, tankID: int):
        super().__init__(6 if side ^ tankID else 2, side * 8, FieldItemType.Tank)
        self.side = side
        self.tankID = tankID

class TankField:

    def __init__(self):
        self.fieldContent = [
            [[] for x in range(FIELD_WIDTH)] for y in range(FIELD_HEIGHT)
        ]
        self.tanks = [[Tank(s, t) for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]
        self.bases = [Base(s) for s in range(SIDE_COUNT)]
        self.lastActions = [[Action.Invalid for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]
        self.actions = [[Action.Invalid for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]
        self.currentTurn = 1

        for tanks in self.tanks:
            for tank in tanks:
                self.insertFieldItem(tank)
        for base in self.bases:
            self.insertFieldItem(base)
        self.insertFieldItem(FieldObject(4, 1, FieldItemType.Steel))
        self.insertFieldItem(FieldObject(4, 7, FieldItemType.Steel))

    def insertFieldItem(self, item: FieldObject):
        self.fieldContent[item.y][item.x].append(item)
        item.destroyed = False

    def removeFieldItem(self, item: FieldObject):
        self.fieldContent[item.y][item.x].remove(item)
        item.destroyed = True

    def fromBinary(self, bricks: List[int]):
        for i in range(3):
            mask = 1
            for y in range(i * 3, i * 3 + 3):
                for x in range(FIELD_WIDTH):
                    if bricks[i] & mask:
                        self.insertFieldItem(FieldObject(x, y, FieldItemType.Brick))
                    mask = mask << 1

    def actionValid(self, side: int, tank: int, action: Action) -> bool:
        if action >= Action.UpShoot and self.lastActions[side][tank] >= Action.UpShoot:
            return False
        if action == Action.Stay or action >= Action.UpShoot:
            return True
        x = self.tanks[side][tank].x + dx[action]
        y = self.tanks[side][tank].y + dy[action]
        return self.inRange(x, y) and not self.fieldContent[y][x]

    def allValid(self) -> bool:
        for tanks in self.tanks:
            for tank in tanks:
                if not tank.destroyed and not self.actionValid(tank.side, tank.tankID, self.actions[tank.side][tank.tankID]):
                    return False
        return True

    def inRange(self, x: int, y: int) -> bool:
        return x >= 0 and x < FIELD_WIDTH and y >= 0 and y < FIELD_HEIGHT

    def setActions(self, side: int, actions: List[int]) -> bool:
        if self.actionValid(side, 0, actions[0]) and self.actionValid(side, 1, actions[1]):
            self.actions[side] = actions
            return True
        return False

    def doActions(self) -> bool:
        if not self.allValid():
            return False

        self.lastActions = self.actions.copy()

        for tanks in self.tanks:
            for tank in tanks:
                action = self.actions[tank.side][tank.tankID]
                if not tank.destroyed and action >= Action.Up and action < Action.UpShoot:
                    self.removeFieldItem(tank)
                    tank.x = tank.x + dx[action]
                    tank.y = tank.y + dy[action]
                    self.insertFieldItem(tank)

        itemsToBeDestroyed = set()

        for tanks in self.tanks:
            for tank in tanks:
                action = self.actions[tank.side][tank.tankID]
                if not tank.destroyed and action >= Action.UpShoot:
                    x = tank.x
                    y = tank.y
                    action = action % 4
                    multipleTankWithMe = len(self.fieldContent[y][x]) > 1
                    while True:
                        x = x + dx[action]
                        y = y + dy[action]
                        if not self.inRange(x, y):
                            break
                        collides = self.fieldContent[y][x]
                        if collides:
                            if not multipleTankWithMe and len(collides) == 1 and collides[0].itemType == FieldItemType.Tank:
                                oppAction = self.actions[collides[0].side][collides[0].tankID]
                                if oppAction >= Action.UpShoot and action == (oppAction + 2) % 4:
                                    break
                            itemsToBeDestroyed.update(collides)
                            break

        for item in itemsToBeDestroyed:
            if item.itemType != FieldItemType.Steel:
                self.removeFieldItem(item)

        self.currentTurn = self.currentTurn + 1
        self.actions = [[Action.Invalid for t in range(TANK_PER_SIDE)] for s in range(SIDE_COUNT)]

    def sideLose(self, side: int) -> bool:
        return (self.tanks[side][0].destroyed and self.tanks[side][1].destroyed) or self.bases[side].destroyed

    def whoWins(self) -> WhoWins:
        fail = [self.sideLose(s) for s in range(SIDE_COUNT)]
        if fail[0] == fail[1]:
            return WhoWins.Draw if fail[0] or self.currentTurn > 100 else WhoWins.NotFinished
        if fail[0]:
            return WhoWins.Red
        return WhoWins.Blue

class BotzoneIO:
    def __init__(self, longRunning = False):
        self.longRunning = longRunning
        self.mySide = -1
        self.data = None
        self.globaldata = None

    def _processItem(self, field: TankField, item, isOpponent: bool):
        if isinstance(item, dict):
            self.mySide = item['mySide']
            field.fromBinary(item['field'])
        elif isOpponent:
            field.setActions(1 - self.mySide, item)
            field.doActions()
        else:
            field.setActions(self.mySide, item)

    def readInput(self, field: TankField):
        string = input()
        obj = json.loads(string)
        if 'requests' in obj:
            requests = obj['requests']
            responses = obj['responses']
            n = len(requests)
            for i in range(n):
                self._processItem(field, requests[i], True)
                if i < n - 1:
                    self._processItem(field, responses[i], False)

            if 'data' in obj:
                self.data = obj['data']
            if 'globaldata' in obj:
                self.globaldata = obj['globaldata']
        else:
            self._processItem(field, obj, True)

    def writeOutput(self, actions: List[Action], debug: str = None, data: str = None, globaldata: str = None, exitAfterOutput = False):
        print(json.dumps({
            'response': actions,
            'debug': debug,
            'data': data,
            'globaldata': globaldata
        }))
        if exitAfterOutput:
            exit(0)
        else:
            print(">>>BOTZONE_REQUEST_KEEP_RUNNING<<<")
            sys.stdout.flush()

if __name__ == '__main__':
    field = TankField()
    io = BotzoneIO()
    while True:
        io.readInput(field)

        myActions = []
        for tank in range(TANK_PER_SIDE):
            availableActions = [
                action for action in range(Action.Stay, Action.LeftShoot + 1) if field.actionValid(io.mySide, tank, action)
            ]
            myActions.append(random.choice(availableActions))

        io.writeOutput(myActions, "DEBUG!", io.data, io.globaldata, False)
        field.setActions(io.mySide, myActions)