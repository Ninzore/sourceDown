import os
import re
import asyncio
from datetime import datetime, timedelta

from . import config

FILEPATH = config.dl_root
AUTO_CLEAN_INTERVAL = config.auto_clean_interval

def deleteByName(search_ptn: str):
    ptn = re.compile(search_ptn)
    for (dirpath, dirnames, filenames) in os.walk(FILEPATH):
        for f in filenames:
            if ptn.search(f):
                try:
                    filepath = os.path.join(dirpath, f)
                    os.unlink(filepath)
                    print('已删除', f)
                except Exception as err:
                    print(f'删除{f}时出错: ', err)

def deleteByTime(max_timedelta: timedelta):
    for (dirpath, dirnames, filenames) in os.walk(FILEPATH):
        for f in filenames:
            try:
                filepath = os.path.join(dirpath, f)
                stat = os.stat(filepath)
                if datetime.now() - max_timedelta > datetime.fromtimestamp(stat.st_ctime):
                    os.unlink(filepath)
                    print('已删除', f)
            except Exception as err:
                print(f'删除{f}时出错: ', err)

def autocleanOutdated(max_timedelta: timedelta):
    async def task():
        while True:
            deleteByTime(max_timedelta)
            await asyncio.sleep(60)

    async def task_():
        try:
            await task()
        except Exception as err:
            print('autocleanOutdated 中途错误: ', err, '重启任务')
            await task()

def startAutoCleanTask():
    asyncio.get_event_loop().run_in_executor(None, autocleanOutdated, AUTO_CLEAN_INTERVAL)    
