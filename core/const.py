# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 21:18:11
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 04:15:52

#{ BEGIN }#

#-----------------#
# Release Version #
#-----------------#
DEBUG_MODE        = False
LONG_RUNNING_MODE = False

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


DIRECTIONS_UDLR = ( (0,-1), (0,1), (-1,0), (1,0) ) # 上下左右移动

#{ END }#


#------------#
# Debug Mode #
#------------#
DEBUG_MODE        = True
LONG_RUNNING_MODE = True