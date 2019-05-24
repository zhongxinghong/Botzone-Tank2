# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 14:38:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-23 19:14:09
"""
定时任务调度器
---------------------
定期从 botzone 上下载特定的信息


定时任务
------------
1. 每  6 小时 重新登录一次，保证 cookies 有效
2. 每 10 分钟 下载一次目标 bot 的天梯对局记录
3. 每  1 分钟 下载一次有目标 bot 参加的全局对局记录

开机任务
------------
1. 登录一次
2. 获取天梯对局记录一次
3. 获取从上次停止到现在的所有漏掉的比赛记录，如果是第一次开机，则忽略这个任务

"""

import time
from apscheduler.schedulers.background import BackgroundScheduler
from _lib.scheduler.tasks import (

    task_botzone_login,
    task_download_favorite_matches,
    task_download_rank_matches,
    task_download_global_matches,
    task_download_previous_global_matches,
    task_download_contest_matches,

)



def main():

    ## 所有事件均预先执行一次 ##
    task_botzone_login()
    task_download_favorite_matches()
    task_download_rank_matches()
    # task_download_global_matches()

    ## 只执行一次的特殊事件 ##
    task_download_previous_global_matches()
    #task_download_contest_matches()


    scheduler = BackgroundScheduler()

    scheduler.add_job(task_botzone_login, "interval", hours=6, id="botzone_login")
    scheduler.add_job(task_download_favorite_matches, "interval", minutes=5, id="download_favorite_matches")
    scheduler.add_job(task_download_rank_matches, "interval", minutes=10, id="download_rank_matches")
    scheduler.add_job(task_download_global_matches, "interval", minutes=1, id="download_global_matches")

    scheduler.start()


    try:
        while True:  # 自定义 block
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit) as e:
        scheduler.shutdown(wait=False)


if __name__ == '__main__':
    main()
