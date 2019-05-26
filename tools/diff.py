# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-26 06:48:31
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-26 07:17:32
"""
比较 diff_files/ 下两个 *.py 文件的差异

比较结果将会输出到 diff_files/ 下

"""

import os
import difflib
from _lib.utils import get_abspath


DIFF_FILES_DIR   = get_abspath("./diff_files/")
OUTPUT_DIFF_HTML = get_abspath("./diff_files/diff_result.html")

SHOW_ALL = False  # 是否显示文件的所有内容，False 则只显示差异部分
NUMLINES = 10     # 差异位置上下文显示的行数


def main():

    pys = [ filename for filename in os.listdir(DIFF_FILES_DIR) if filename.endswith(".py") ]

    assert len(pys) == 2, "There must be two *.py in %s" % DIFF_FILES_DIR

    file1, file2 = [ os.path.join(DIFF_FILES_DIR, filename) for filename in pys ]

    with open(file1, "r", encoding="utf-8") as fp:
        content1 = fp.readlines()

    with open(file2, "r", encoding="utf-8") as fp:
        content2 = fp.readlines()

    d = difflib.HtmlDiff()
    res = d.make_file(content1, content2, file1, file2,
                context= not SHOW_ALL, numlines=NUMLINES)

    with open(OUTPUT_DIFF_HTML, "w", encoding="utf-8") as fp:
        fp.write(res)


if __name__ == '__main__':
    main()

