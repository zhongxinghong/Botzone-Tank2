# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 06:10:25
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-07 21:56:35
"""
项目自动化构建工具
--------------------------
将多个源文件合并为一个单文件

- ./config/builder.json  配置项及源文件列表，程序会按照先后顺序进行合并
- ../build/main.py       目标输出文件


代码区域的标记方式：

#{ BEGIN }#

    Your codes here ...

#{ END }#

注：一个文件中可以有一个或多个代码区域

"""

import os
import time
from _lib.utils import abs_path, mkdir, read_file, json_load
from _lib.builder.const import BLANK_LINES, BUILD_DIR, CONFIG_JSON_FILE
from _lib.builder.bean import SourceBean
from _lib.builder.parser import extract_code


config = json_load(CONFIG_JSON_FILE)

AUTHOR       = config["header"]["author"]
LICENSE_FILE = config["header"]["license"]
DESCRIPTION  = config["header"]["description"]
SITE         = config["header"]["site"]
FILENAME     = config["filename"]
SOURCES_LIST = config["sources"]

OUTPUT_FILE  = os.path.join(BUILD_DIR, FILENAME)

LICENSE      = read_file(LICENSE_FILE) if LICENSE_FILE else None

HEADER = f'''\
# -*- coding: utf-8 -*-
# @author:      { AUTHOR }
# @filename:    { FILENAME }
# @date:        { time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) }
# @site:        { SITE }
# @description: { DESCRIPTION or "" }
'''

if LICENSE is not None:
    HEADER += f'"""\n{ LICENSE.strip() }\n"""'


def main():

    mkdir(BUILD_DIR) # 创建文件将爱

    fp = open(OUTPUT_FILE, "w", encoding="utf-8")

    fp.write(HEADER)
    fp.write(BLANK_LINES)

    for _src in SOURCES_LIST:

        src = SourceBean(_src)
        if src.disabled:
            continue

        file     = src.file
        fullname = src.fullname

        fp.write("#{ BEGIN %r }#" % fullname)
        fp.write(BLANK_LINES)
        content = read_file(file)
        code = extract_code(content)
        fp.write(code)
        fp.write(BLANK_LINES)

        fp.write("#{ END %r }#" % fullname)
        fp.write(BLANK_LINES * 2)

    fp.close()


if __name__ == '__main__':
    main()
