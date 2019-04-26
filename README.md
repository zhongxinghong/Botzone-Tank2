Botzone-Tank2
===============
19年春季学期程设 AI 对抗赛 Tank2 的 bot



开发与测试环境
---------------
- Python 3.6.2



项目构建方法
---------------

### 自动化构建工具

在 `script/build.py` 中的 `PYs` 变量下依次添加需要合并的 `*.py` 文件，
然后在相应文件中使用 `#{ BEGIN }#` 和 `#{ END }#` 记号标注代码区域，
最后运行 `script/build.py` 脚本，即可在 `build/` 文件夹下构建一个单文件版的
`main.py` 脚本，可以用于代码提交。


### 官方建议

Botzone 对 Python 多文件的官方处理建议是： 在工程的根目录创建 `__main__.py` 文件
作为入口，然后将整个工程打包成 ZIP 上传。



测试说明
--------------

### DEBUG_MODE

在 `const.py` 内定义了一个常数 `DEBUG_MODE` ，如果使用自动化构建工具生成代码
则该常数值为 `False` ，否则为 `True` 。可以通过这个常数值来区分运行环境。


### LONG_RUNNING_MODE

在 `const.py` 内同样定义了一个常数 `LONG_RUNNING_MODE` ，在上传时为 `False`
每回合决策结束后会调用 `sys.exit(0)` 退出。测试环境下为 `True` ，可以多回合决策。


### 测试模式下的特征

1. 有 log 输出
