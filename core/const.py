# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 21:18:11
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-30 16:23:18
"""
全局常数
"""

#{ BEGIN }#

#----------------------#
# Environment Variable #
#----------------------#
DEBUG_MODE        = False
LONG_RUNNING_MODE = False
SIMULATOR_ENV     = False
COMPACT_MAP       = False
SIMULATOR_PRINT   = True

#-------------#
# Game Config #
#-------------#
MAP_HEIGHT     = 9
MAP_WIDTH      = 9
SIDE_COUNT     = 2
TANKS_PER_SIDE = 2

#-------------#
# Game Status #
#-------------#
GAME_STATUS_NOT_OVER = -2
GAME_STATUS_DRAW     = -1
GAME_STATUS_BLUE_WIN = 0
GAME_STATUS_RED_WIN  = 1

BLUE_SIDE = 0
RED_SIDE  = 1

DIRECTIONS_URDL = ( (0,-1), (1,0), (0,1), (-1,0) ) # 上右下左，与行为一致


#{ END }#


#------------#
# Debug Mode #
#------------#
DEBUG_MODE        = True