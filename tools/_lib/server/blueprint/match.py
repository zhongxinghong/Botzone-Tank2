# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-23 16:26:17
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 16:49:21

import os
import math
from flask import Blueprint, render_template, jsonify, request, abort
from ...scheduler.const import GLOBAL_MATCHES_DATA_DIR, RANK_MATCHES_DATA_DIR,\
                                CONTEST_MATCHES_DATA_DIR
from ...server.const import STATIC_DIR, TEMPLATES_DIR, MATCHES_PER_PAGE
from ...server.config import AppConfig
from ...utils import json_load


bpMatch = Blueprint("match", __name__, url_prefix="/matches")


_MATCHES_DIR_MAP = {

    "rank": RANK_MATCHES_DATA_DIR,
    "global": GLOBAL_MATCHES_DATA_DIR,
    "contest": CONTEST_MATCHES_DATA_DIR,

    }


def _render_matches(data_dir, template):
    page = int(request.args.get("page", 1))
    assert page > 0
    filenames = list(sorted(os.listdir(data_dir), reverse=True))
    totalPage = math.ceil( len(filenames) / MATCHES_PER_PAGE )
    assert page <= totalPage
    filenames = filenames[ (page-1)*MATCHES_PER_PAGE : page*MATCHES_PER_PAGE ] # 截取比赛记录

    matches = []
    for filename in filenames:
        file = os.path.join(data_dir, filename)
        match = json_load(file)
        match["bots"]    = [ item[0] for item in match["players"] ]
        match["players"] = [ item[1] for item in match["players"] ]
        matches.append(match)
    for idx, match in enumerate(matches):
        match["listID"]  = MATCHES_PER_PAGE*(page-1) + idx + 1
    return render_template(template, matches=matches, current_page=page, total_page=totalPage)


@bpMatch.route("/rank")
def rank_matches_list():
    return _render_matches(RANK_MATCHES_DATA_DIR, "rank_matches.html")

@bpMatch.route("/global")
def global_matches_list():
    return _render_matches(GLOBAL_MATCHES_DATA_DIR, "global_matches.html")

@bpMatch.route("/contest")
def contest_matches_list():
    return _render_matches(CONTEST_MATCHES_DATA_DIR, "contest_matches.html")


@bpMatch.route("/<matchType>/<matchID>", methods=["DELETE"])
def api_match(matchType, matchID):

    _DIR = _MATCHES_DIR_MAP.get(matchType)
    if _DIR is None:
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