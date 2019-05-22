# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-21 15:15:46
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-22 00:29:40
"""
本地 botzone 服务器

以网页的形式呈现本地存储的比赛记录数据
目前只支持显示双人比赛的对局结果

"""

import os
import math
from flask import Flask, render_template, jsonify, redirect, url_for, request, abort
from _lib.scheduler.const import GLOBAL_MATCHES_DATA_DIR, RANK_MATCHES_DATA_DIR
from _lib.server.const import STATIC_DIR, TEMPLATES_DIR, MATCHES_PER_PAGE
from _lib.server.config import AppConfig
from _lib.utils import json_load


app = Flask("botzone", static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
app.config.from_object(AppConfig)
AppConfig.init_app(app)


@app.route("/favicon.ico")
def favicon_ico():
    return redirect(url_for("static", filename="assets/icons/favicon.ico"))

@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/matches/rank")
def rank_matches_list():
    page = int(request.args.get("page", 1))
    assert page > 0
    filenames = list(sorted(os.listdir(RANK_MATCHES_DATA_DIR), reverse=True))
    totalPage = math.ceil( len(filenames) / MATCHES_PER_PAGE )
    assert page <= totalPage
    filenames = filenames[ (page-1)*MATCHES_PER_PAGE : page*MATCHES_PER_PAGE ] # 截取比赛记录

    matches = []
    for filename in filenames:
        file = os.path.join(RANK_MATCHES_DATA_DIR, filename)
        match = json_load(file)
        match["bots"]    = [ item[0] for item in match["players"] ]
        match["players"] = [ item[1] for item in match["players"] ]
        matches.append(match)
    for idx, match in enumerate(matches):
        match["listID"]  = MATCHES_PER_PAGE*(page-1) + idx + 1
    return render_template("rank_matches.html", matches=matches, current_page=page, total_page=totalPage)


@app.route("/matches/global")
def global_matches_list():
    page = int(request.args.get("page", 1))
    assert page > 0
    filenames = list(sorted(os.listdir(GLOBAL_MATCHES_DATA_DIR), reverse=True))
    totalPage = math.ceil( len(filenames) / MATCHES_PER_PAGE )
    assert page <= totalPage
    filenames = filenames[ (page-1)*MATCHES_PER_PAGE : page*MATCHES_PER_PAGE ] # 截取比赛记录

    matches = []
    for filename in filenames:
        file = os.path.join(GLOBAL_MATCHES_DATA_DIR, filename)
        match = json_load(file)
        match["bots"]    = [ item[0] for item in match["players"] ]
        match["players"] = [ item[1] for item in match["players"] ]
        matches.append(match)
    for idx, match in enumerate(matches):
        match["listID"]  = MATCHES_PER_PAGE*(page-1) + idx + 1
    return render_template("global_matches.html", matches=matches, current_page=page, total_page=totalPage)


@app.route("/matches/<matchType>/<matchID>", methods=["DELETE"])
def api_match(matchType, matchID):

    if matchType == "global":
        _DIR = GLOBAL_MATCHES_DATA_DIR
    elif matchType == "rank":
        _DIR = RANK_MATCHES_DATA_DIR
    else:
        abort(404)

    if request.method == "DELETE":

        file = os.path.join( _DIR, "%s.json" % matchID )
        if not os.path.exists(file):
            return jsonify({
                "errcode": 1,
                "errmsg": "Match %s is not Found" % matchID,
                })
        else:
            os.remove(file)
            return jsonify({
                "errcode": 0,
                "errmsg": "success",
                })

    else:
        abort(405)


if __name__ == '__main__':
    app.run(debug=True)