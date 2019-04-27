Botzone-Tank2
===============
19年春季学期程设 AI 对抗赛 Tank2 的 bot



开发与测试环境
---------------
- Python 3.6.2



项目构建方法
---------------

### 项目构建工具

详见 `script/build.py`


### 官方建议

Botzone 对 Python 多文件的官方处理建议是： 在工程的根目录创建 `__main__.py` 文件
作为入口，然后将整个工程打包成 ZIP 上传。


开发说明
--------------
1. 所有全局 module 均从 `global_.py` 中导入，然后再统一从 `global_.py` 中导入到
各个文件。


测试说明
--------------

### DEBUG_MODE

在 `const.py` 内定义了一个常数 `DEBUG_MODE` ，在上传版本中为 `False` ，在本地测试
为 `True` 。可以通过这个常数值来区分运行环境，从而针对性地添加特定的运行行为。


### LONG_RUNNING_MODE

在 `const.py` 内同样定义了一个常数 `LONG_RUNNING_MODE` ，在上传版本中为 `False`
每回合决策结束后会调用 `sys.exit(0)` 退出。本地测试环境下为 `True` ，可以多回合决策。


### 测试模式下的特征

1. 有 log 输出
