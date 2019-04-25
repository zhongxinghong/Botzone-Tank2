# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:04:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 09:20:13

#{ BEGIN }#
import random
#{ END }#
from core.botzone import Tank2Botzone
from core.action import Action
from core.map_ import Tank2Map
from core.const import MAP_WIDTH, MAP_HEIGHT, TANKS_PER_SIDE
from core.stream import BotzoneIstream, BotzoneOstream

#{ BEGIN }#

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


#{ END }#