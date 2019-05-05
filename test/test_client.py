# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 14:56:48
# @Last Modified by:   zhongxinghong
# @Last Modified time: 2019-05-05 17:34:15

import sys
sys.path.append("../")

import os
import re
from requests.compat import json
from pprint import pprint
from lxml import etree
from tools._lib.client.botzone import BotzoneClient
from tools._lib.client.bean import BotBean, GameBean, MatchBean, BotPlayerBean
from tools._lib.const import CACHE_DIR

client = BotzoneClient()

#client.login()
#r = client.get_mybots()

reScore = re.compile(r'\d+(?:\.\d+)?')

with open(os.path.join(CACHE_DIR, "mybots.html"), "rb") as fp:
    content = fp.read()

tree = etree.HTML(content)

games = [GameBean(gameTree) for gameTree
            in tree.xpath('.//div[@id="games"]/div[not(contains(@style, "display: none"))]')]

'''
for gameTree in games:
    gameName = gameTree.xpath('.//*[contains(@class, "panel-title")]/text()')[0].strip()
    gameID = gameTree.xpath('./ul/@id')[0].lstrip("game")

    print(gameName)
    print(gameID)

    for botTree in gameTree.xpath('./ul/li'):

        botID = botTree.xpath('./a/@data-botid')[0]
        gameID = botTree.xpath('./a/@data-gameid')[0]
        botName = botTree.xpath('.//*[@class="list-group-item-heading"]/text()')[0]
        botVersion = int(botTree.xpath('.//*[contains(@class, "botversion")]/span/text()')[0])
        botDescription = botTree.xpath('.//*[contains(@class, "botdesc")]/text()')[0]
        _botScoreText = botTree.xpath('.//*[contains(@class, "rankscore")]/text()')[0]
        botScore = reScore.search(_botScoreText).group()


        print(botID)
        print(botName)
        print(botVersion)
        print(botDescription)
        print(botScore)
'''

botID = games[0].bots[1].id

#print(botID)

#r = client.get_bot_detail(botID)

with open(os.path.join(CACHE_DIR, "bot_detail_5cc70d6275e55951524caa17.json"), "rb") as fp:
    botDetailJSON = json.load(fp)


matches = [MatchBean(match) for match in botDetailJSON["bot"]["rank_matches"]]

pprint(matches)

match = matches[0]

print(match.dict)


#print(r.content)


