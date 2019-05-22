# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-21 15:31:37
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-22 00:07:43

__all__ = [

    "STATIC_DIR",
    "TEMPLATES_DIR",

    "MATCHES_PER_PAGE",

    ]

from ..utils import get_abspath


STATIC_DIR    = get_abspath("./server/static/")
TEMPLATES_DIR = get_abspath("./server/templates/")

MATCHES_PER_PAGE = 30