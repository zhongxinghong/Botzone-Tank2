# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 06:10:25
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-25 10:25:02

import os
import re
import time

from utils import mkdir, read_file


BLANK_LINES = "\n\n"


_Regex_Code = re.compile(r"#{\s*BEGIN\s*}#\s*(.*?)\s*#{\s*END\s*}#", re.I|re.S)

def extract_code(content):
    res = _Regex_Code.findall(content)
    if len(res) == 0:
        raise Exception
    return BLANK_LINES.join(res)


os.chdir(os.path.dirname(__file__)) # 确保相对路径指向正确

ROOT_DIR = "../"
CORE_DIR = "../core/"
BUILD_DIR = "../build"

mkdir(BUILD_DIR)


PYs = [

    "../core/const.py",
    "../core/stream.py",
    "../core/botzone.py",
    "../core/action.py",
    "../core/field.py",
    "../core/map_.py",
    "../core/strategy.py",
    "../main.py",

    ]


OUTPUT_PY = "../build/main.py"


HEADER = f"""\
# -*- coding: utf-8 -*-
# @Author:   Rabbit
# @Filename: {os.path.basename(OUTPUT_PY)}
# @Date:     {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}
# @Description: Auto-built single-file Python script for Botzone/Tank2
"""


wfp = open(OUTPUT_PY, "w", encoding="utf-8")

wfp.write(HEADER)
wfp.write(BLANK_LINES)

for file in PYs:

    filename = os.path.basename(file)

    wfp.write(f"# BEGIN {filename} #")
    wfp.write(BLANK_LINES)

    content = read_file(file)
    code = extract_code(content)
    wfp.write(code)
    wfp.write(BLANK_LINES)

    wfp.write(f"# END {filename} #")
    wfp.write(BLANK_LINES * 2)

wfp.close()

