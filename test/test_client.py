# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 14:56:48
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 18:14:29

import sys
sys.path.append("../")

import os
import re
from requests.compat import json
from pprint import pprint
from lxml import etree
from tools._lib.client.botzone import BotzoneClient
from tools._lib.client.bean import RankBotBean, RankGameBean, RankMatchBean, RankBotPlayerBean,\
    GlobalMatchBean, GlobalMatchPlayerBean, GroupContestMatchBean, GroupContestBean
from tools._lib.const import CACHE_DIR

client = BotzoneClient()

#client.login()
#r = client.get_mybots()
#client.get_global_match_list(gameID="5c908e0e7857b210f901be7d")

reScore = re.compile(r'\d+(?:\.\d+)?')
reBotIDFromFavorite = re.compile(r'AddFavoriteBot\(this,\s*\'(\S+?)\',\s*(?:\d+)\)')


with open(os.path.join(CACHE_DIR, "mybots.html"), "rb") as fp:
    content = fp.read()


tree = etree.HTML(content)

games = [RankGameBean(gameTree) for gameTree
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


matches = [RankMatchBean(match) for match in botDetailJSON["bot"]["rank_matches"]]

pprint(matches)

match = matches[0]

print(match.dict)

with open(os.path.join(CACHE_DIR, "global_match_list.html"), "rb") as fp:
    content = fp.read()

tree = etree.HTML(content)
trs = tree.xpath('//body/div[@class="container"]//table//tr[position()>1]')

### global_match_list ###

'''
for tr in trs:

    matchTime = tr.xpath('./td[1]/text()')[0]
    gameName  = tr.xpath('./td[2]/a/text()')[0]
    matchID   = tr.xpath('./td[5]/a/@href')[0].split("/")[-1]
    players   = tr.xpath('./td[4]/div[contains(@class, "matchresult")]')


    print(matchTime)
    print(gameName)
    print(matchID)

    for _div in players:

        userName = _div.xpath('./a[@class="username" or @class="smallusername"]/text()')[0]
        userID = _div.xpath('./a[@class="username" or @class="smallusername"]/@href')[0].split("/")[-1]
        score = int(_div.xpath('./div[1]/text()')[0])

        isBot = "botblock" in _div.attrib["class"]

        print(userName)
        print(userID)
        print(score)
        print(isBot)

        if isBot:
            _a = _div.xpath('./a[contains(@class, "botname")]')[0]
            botName = _a.text.strip()
            botID = reBotIDFromFavorite.match(_div.xpath('./a[contains(@class, "favorite")]/@onclick')[0]).group(1)
            botVersion = int(_a.xpath('./span[@class="version"]/text()')[0])
            print(botName)
            print(botID)
            print(botVersion)

'''
'''
for match in [ GlobalMatchBean(tr) for tr in trs ]:
    print(match)
    print(match.dict)
    for player in match.players:
        print(player)
'''


### contest_detail ###

contestID = "5cbeb05f35f461309c26da61"
groupID   = "5cb5794383f1e10a1eddebb3"
game      = "Tank2"
#r = client.get_contest_detail(contestID, groupID)
#print(r.content) # 哇塞... 真踏马的大... 怪不着昨晚用手机看比赛掉了这么多流量...

with open(os.path.join(CACHE_DIR, "contest_detail.json"), "rb") as fp:
    contentDetailJSON = json.load(fp)

tableHTML = contentDetailJSON["table"] #.encode("utf-8")
'''with open(os.path.join(CACHE_DIR, "contest_detail_matches.html"), "wb") as fp:
    fp.write(tableHTML)'''

#tree = etree.HTML(tableHTML) # 显式指定为 utf-8 编码，否则容易乱码

#trs = tree.xpath(".//tr")

'''for match in [ GroupContestMatchBean(tr, contestID, groupID) for tr in trs ]:
    print(match)
    print(match.dict)
    for player in match.players:
        print(player)'''

contest = GroupContestBean(contentDetailJSON, game)

print(contest)
print(contest.players[0])
pprint(contest.matches[0].dict)

r = client.get_favorites()