# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-04 02:45:34
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-21 15:31:19

__all__ = [

    "CONFIG_JSON_FILE",

    ]

from ..utils import get_abspath


CONFIG_JSON_FILE = get_abspath("./config/autotest.json")