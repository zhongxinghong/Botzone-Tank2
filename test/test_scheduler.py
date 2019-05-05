# -*- coding: utf-8 -*-
# @Author: Administrator
# @Date:   2019-05-05 22:56:18
# @Last Modified by:   Administrator
# @Last Modified time: 2019-05-05 23:11:14

import time
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler

#logging.basicConfig()
#logging.getLogger('apscheduler').setLevel(logging.DEBUG)

#scheduler = BlockingScheduler()
scheduler = BackgroundScheduler()


def task_1():
    print("task_1 ok !")


def task_2():
    print("no !")
    print( 1 / 0 )


scheduler.add_job(task_1, "interval", seconds=3, id="task_1")
scheduler.add_job(task_2, "interval", seconds=3, id="task_2")

scheduler.start()

try:
    while True:
        time.sleep(5)
except (KeyboardInterrupt, SystemExit) as e:
    scheduler.shutdown(wait=False)

