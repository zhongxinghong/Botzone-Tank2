# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-23 16:26:11
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 16:40:50

from flask import Blueprint, redirect, url_for, render_template


bpRoot = Blueprint("root", __name__)


@bpRoot.route("/favicon.ico")
def favicon_ico():
    return redirect(url_for("static", filename="assets/icons/favicon.ico"))

@bpRoot.route("/robots.txt")
def robots_txt():
    return redirect(url_for("static", filename="robots.txt"))

@bpRoot.route("/")
@bpRoot.route("/home")
def home():
    return render_template("home.html")