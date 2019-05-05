# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 14:38:20
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-05 23:14:10
"""
定时任务调度

1. 每 6 小时 重新登录一次，保证 cookies 有效
2. 每 5 分钟 下载一次天梯记录

"""

import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from _lib.scheduler.rank import task_botzone_login, task_download_rank_matches


def main():

    task_botzone_login()         # 先登录一次
    task_download_rank_matches() # 先下载一次天梯比赛记录

    #scheduler = BlockingScheduler()
    scheduler = BackgroundScheduler()

    scheduler.add_job(task_botzone_login, "interval", hours=6, id="botzone_login")
    scheduler.add_job(task_download_rank_matches, "interval", minutes=5, id="download_rank_matches")

    scheduler.start()

    try:
        while True:  # 自定义的阻塞
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit) as e:
        scheduler.shutdown(wait=False)


if __name__ == '__main__':
    main()