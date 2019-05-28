# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-28 17:14:33
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-28 17:29:28

import os
from flask import Blueprint, request, jsonify

from ...client.botzone import BotzoneClient
from ...client.bean.contest import GroupContestBean
from ...scheduler.const import CONFIG_JSON_FILE, CONTEST_MATCHES_DATA_DIR
from ...utils import json_load, json_dump


bpDownload = Blueprint("download", __name__, url_prefix="/download")

@bpDownload.route("/contest/<groupID>/<contestID>")
def download_contest(groupID, contestID):

    config = json_load(CONFIG_JSON_FILE)
    botID = request.args.get("botID", config["contest_match"]["bot_id"] )
    game  = request.args.get("game", config["contest_match"]["game"] )

    try:
        _client = BotzoneClient()
        r = _client.get_contest_detail(contestID, groupID)
        contest = GroupContestBean(r.json(), game)
        counter = 0
        for match in contest.matches:
            file = os.path.join(CONTEST_MATCHES_DATA_DIR, "%s.json" % match.id)
            if os.path.exists(file):
                continue
            for bot in match.players:
                if bot.id == botID:
                    json_dump(match.dict, file, ensure_ascii=False, indent=4)
                    counter += 1

        return jsonify({
            "errcode": 0,
            "contestID": contestID,
            "groupID": groupID,
            "botID": botID,
            "game": game,
            "new_matches": counter,
            })

    except Exception as e:
        return jsonify({
            "errcode": -1,
            "errmsg": repr(e)
            })
