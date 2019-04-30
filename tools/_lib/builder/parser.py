# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-01 02:07:50
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-01 02:29:57

__all__ = [

    "extract_code",

    ]


import re
from .const import BLANK_LINES


_Regex_Code = re.compile(r"#{\s*BEGIN\s*}#\s*(.*?)\s*#{\s*END\s*}#", re.I|re.S)


def extract_code(content):
    res = _Regex_Code.findall(content)
    if len(res) == 0:
        raise Exception(r"No zone #{ BEGIN }#{code}#{ END }#, " + "content:\n" + content)
    return BLANK_LINES.join(res)
