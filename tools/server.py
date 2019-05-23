# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-21 15:15:46
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 16:32:33
"""
本地 botzone 服务器

以网页的形式呈现本地存储的比赛记录数据
目前只支持显示双人比赛的对局结果

"""

from flask import Flask
from _lib.server.const import STATIC_DIR, TEMPLATES_DIR
from _lib.server.config import AppConfig
from _lib.server.blueprint import bpRoot, bpMatch


app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)


app.config.from_object(AppConfig)
AppConfig.init_app(app)

app.register_blueprint(bpRoot)
app.register_blueprint(bpMatch)


if __name__ == '__main__':
    app.run(debug=True)