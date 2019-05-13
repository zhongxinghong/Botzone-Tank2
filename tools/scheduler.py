# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 14:38:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-14 04:22:42
"""
定时任务

1. 每  6 小时 重新登录一次，保证 cookies 有效
2. 每 15 分钟 下载一次目标 bot 的天梯对局记录
3. 每  2 分钟 下载一次有目标 bot 参加的全局对局记录

"""

import time
from apscheduler.schedulers.background import BackgroundScheduler
from _lib.scheduler.tasks import task_botzone_login, task_download_rank_matches, task_download_global_matches


def main():

    ## 所有事件均预先执行一次
    task_botzone_login()
    task_download_rank_matches()
    task_download_global_matches()

    scheduler = BackgroundScheduler()

    scheduler.add_job(task_botzone_login, "interval", hours=6, id="botzone_login")
    scheduler.add_job(task_download_rank_matches, "interval", minutes=15, id="download_rank_matches")
    scheduler.add_job(task_download_global_matches, "interval", minutes=2, id="download_global_matches")

    scheduler.start()

    try:
        while True:  # 自定义 block
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit) as e:
        scheduler.shutdown(wait=False)


if __name__ == '__main__':
    main()