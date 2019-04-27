# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:04:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 18:03:26

from core.const import MAP_WIDTH, MAP_HEIGHT, TANKS_PER_SIDE, LONG_RUNNING_MODE
from core.global_ import time, np
from core.map_ import Tank2Map
from core.strategy import RandomActionStrategy, MoveToWaterStrategy
from core.stream import BotzoneIstream, BotzoneOstream
from core.botzone import Tank2Botzone

#{ BEGIN }#

if __name__ == '__main__':

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_, long_running=LONG_RUNNING_MODE)

    istream = BotzoneIstream()
    ostream = BotzoneOstream()

    while True:

        t1 = time.time()

        if LONG_RUNNING_MODE: # 这个模式下 map 对象会复用，首先需要重置
            map_.reset()

        terminal.handle_input(stream=istream)

        side = terminal.mySide
        tanks = map_.tanks[side]

        '''waterPoints = MoveToWaterStrategy.find_water_points(map_)

        actions = []
        for tank in tanks:
            s = MoveToWaterStrategy(tank, map_, waterPoints)
            action = s.make_decision()
            actions.append(action)'''

        actions = []
        for tank in tanks:
            s = RandomActionStrategy(tank, map_)
            action = s.make_decision()
            actions.append(action)

        t2 = time.time()

        debugInfo = {
            "cost": round(t2 - t1, 3)
            }

        terminal.make_output(actions, stream=ostream, debug=debugInfo)

#{ END }#