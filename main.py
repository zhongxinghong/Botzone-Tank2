# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 22:04:40
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 21:45:12

from core.const import LONG_RUNNING_MODE, SIMULATOR_ENV, MAP_WIDTH, MAP_HEIGHT,\
                        TANKS_PER_SIDE, SIDE_COUNT, BLUE_SIDE, RED_SIDE
from core.global_ import time, np
from core.utils import debug_print, simulator_print
from core.map_ import Tank2Map
from core.action import Action
from core.stream import BotzoneIstream, BotzoneOstream
from core.botzone import Tank2Botzone
from core.player import Tank2Player
from core.team import Tank2Team

#{ BEGIN }#


def main(istream=None, ostream=None):

    map_ = Tank2Map(MAP_WIDTH, MAP_HEIGHT)

    terminal = Tank2Botzone(map_, long_running=LONG_RUNNING_MODE)

    istream = istream or BotzoneIstream()
    ostream = ostream or BotzoneOstream()

    while True:

        t1 = time.time()

        if LONG_RUNNING_MODE: # 这个模式下 map 对象会复用，首先需要重置
            map_.reset()

        terminal.handle_input(stream=istream)

        if SIMULATOR_ENV:
            map_.debug_print_out()

        side = terminal.mySide
        tanks = map_.tanks

        bluePlayer0 = Tank2Player(tanks[BLUE_SIDE][0], map_, terminal.get_past_actions(BLUE_SIDE, 0))
        bluePlayer1 = Tank2Player(tanks[BLUE_SIDE][1], map_, terminal.get_past_actions(BLUE_SIDE, 1))
        redPlayer0  = Tank2Player(tanks[RED_SIDE][0], map_, terminal.get_past_actions(RED_SIDE, 0))
        redPlayer1  = Tank2Player(tanks[RED_SIDE][1], map_, terminal.get_past_actions(RED_SIDE, 1))

        bluePlayer0.set_teammate(bluePlayer1)
        bluePlayer1.set_teammate(bluePlayer0)
        redPlayer0.set_teammate(redPlayer1)
        redPlayer1.set_teammate(redPlayer0)
        bluePlayer0.set_opponents([redPlayer0, redPlayer1])
        bluePlayer1.set_opponents([redPlayer0, redPlayer1])
        redPlayer0.set_opponents([bluePlayer0, bluePlayer1])
        redPlayer1.set_opponents([bluePlayer0, bluePlayer1])

        blueTeam = Tank2Team(BLUE_SIDE, bluePlayer0, bluePlayer1)
        redTeam  = Tank2Team(RED_SIDE, redPlayer0, redPlayer1)
        blueTeam.set_opponent_team(redTeam)
        redTeam.set_opponent_team(blueTeam)

        if side == BLUE_SIDE:
            myPlayer0 = bluePlayer0
            myPlayer1 = bluePlayer1
            myTeam    = blueTeam
            oppTeam   = redTeam
        elif side == RED_SIDE:
            myPlayer0 = redPlayer0
            myPlayer1 = redPlayer1
            myTeam    = redTeam
            oppTeam   = blueTeam
        else:
            raise Exception("unexpected side %s" % side)

        actions = myTeam.make_decision()

        if SIMULATOR_ENV:
            oppActions = oppActions = oppTeam.make_decision()

        if SIMULATOR_ENV:
            _CUT_OFF_RULE = "-" * 20
            simulator_print("Decisions for next turn:")
            simulator_print(_CUT_OFF_RULE)
            _SIDE_NAMES = ["Blue", "Red"]
            for id_, action in enumerate(actions):
                simulator_print("%s %02d: %s" % (_SIDE_NAMES[side], id_+1,
                                    Action.get_name(action)) )
            for id_, action in enumerate(oppActions):
                simulator_print("%s %02d: %s" % (_SIDE_NAMES[1-side], id_+1,
                                    Action.get_name(action)))
            simulator_print(_CUT_OFF_RULE)
            simulator_print("Actually actions on this turn:")
            simulator_print(_CUT_OFF_RULE)
            for side, tanks in enumerate(map_.tanks):
                for id_, tank in enumerate(tanks):
                    simulator_print("%s %02d: %s" % (_SIDE_NAMES[side], id_+1,
                                        Action.get_name(tank.previousAction)))
            simulator_print(_CUT_OFF_RULE)


        t2 = time.time()

        debugInfo = {
            "cost": round(t2-t1, 4),
            }

        terminal.make_output(actions, stream=ostream, debug=debugInfo)


if __name__ == '__main__':
    main()

#{ END }#