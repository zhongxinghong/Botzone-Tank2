# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-24 23:34:32
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-24 23:42:49

import json
from pprint import pprint

inputJSON = json.loads("""
{
    "requests": [
        {
            "field": [64279082, 15466168, 44194142],
            "mySide": 1
        },
        [7, 6],
        [3, 2],
        [2, 6],
        [2, 2],
        [2, 5],
        [6, -1],
        [-1, 7],
        [5, -1],
        [1, 7],
        [4, -1],
        [2, 7],
        [4, -1],
        [3, 7],
        [4, -1],
        [1, 6],
        [4, -1],
        [2, 6],
        [2, -1],
        [2, -1],
        [2, -1],
        [5, -1]
    ],
    "responses": [
        [0, 4],
        [4, 0],
        [0, 4],
        [0, 0],
        [7, 4],
        [-1, 0],
        [7, 0],
        [-1, 4],
        [7, 0],
        [-1, -1],
        [7, -1],
        [-1, 3],
        [-1, -1],
        [4, 1],
        [3, 0],
        [1, 3],
        [4, 5],
        [0, 0],
        [0, 0],
        [0, 5],
        [0, -1]
    ]
}
""")

requests = inputJSON['requests']

firstItem = requests.pop(0)

bricks = firstItem['field']

pprint(bricks)

for i in range(3):
    mask = 1
    for y in range(i * 3, i * 3 + 3):
        for x in range(9):
            if bricks[i] & mask:
                xy = (x, y)
                print(xy, end=" ")
            mask = mask << 1
        print()