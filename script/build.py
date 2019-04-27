# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-04-25 06:10:25
# @Last Modified by:   Administrator
# @Last Modified time: 2019-04-27 17:08:16
"""
项目自动化构建工具
--------------------------
将多个源文件合并为一个单文件


源文件列表： ./src.json         程序会按照先后顺序进行合并
输出单文件： ../build/main.py


代码区域的标记方式：

#{ BEGIN }#
    Your codes here ...
#{ END }#

一个文件中可以有一个或多个代码区域
"""

import os
import re
import time
from _utils import abs_path, mkdir, read_file, json_load


BLANK_LINES  = "\n\n"
SRC_JSON     = abs_path("./src.json")
BUILD_DIR    = abs_path("../build")
OUTPUT_PY    = abs_path("../build/main.py")

HEADER = f"""\
# -*- coding: utf-8 -*-
# @Author:   Rabbit
# @Filename: {os.path.basename(OUTPUT_PY)}
# @Date:     {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}
# @Description: Auto-built single-file Python script for Botzone/Tank2
"""


class SourceBean(object):
    """
    src.json 中每个 src file 的 Bean 类

    struct:　{
        "pacakge": str,
        "file": str,
    }
    """
    def __init__(self, src):
        self._file    = abs_path(src["file"])
        self._package = src["package"]

    @property
    def file(self):
        """
        src file 的绝对路径
        """
        return self._file

    @property
    def package(self):
        r"""
        package 名称，可以添加到 filename 前方

        WARNING:
            - 前后不能带任何 "/", "\" 路径分隔符
        """
        return self._package

    @property
    def filename(self):
        """
        src filename 文件名
        """
        return os.path.basename(self._file)

    @property
    def filenameWithPackage(self):
        """
        添加了 package 前缀的 filename
        """
        _DELIMETER = "/"
        return _DELIMETER.join([self._package, self.filename]).strip(_DELIMETER)



_Regex_Code = re.compile(r"#{\s*BEGIN\s*}#\s*(.*?)\s*#{\s*END\s*}#", re.I|re.S)

def extract_code(content):
    res = _Regex_Code.findall(content)
    if len(res) == 0:
        raise Exception(r"No zone #{ BEGIN }#{code}#{ END }#, " + "content:\n" + content)
    return BLANK_LINES.join(res)



def main():

    mkdir(BUILD_DIR)

    wfp = open(OUTPUT_PY, "w", encoding="utf-8")

    wfp.write(HEADER)
    wfp.write(BLANK_LINES)

    for _src in json_load(SRC_JSON):

        src = SourceBean(_src)

        file     = src.file
        filename = src.filenameWithPackage

        wfp.write("#{ BEGIN %r }#" % filename)
        wfp.write(BLANK_LINES)
        content = read_file(file)
        code = extract_code(content)
        wfp.write(code)
        wfp.write(BLANK_LINES)

        wfp.write("#{ END %r }#" % filename)
        wfp.write(BLANK_LINES * 2)

    wfp.close()


if __name__ == '__main__':
    main()
