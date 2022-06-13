import os
import re
import asyncio
from datetime import datetime, timedelta

from . import config
from .timer import Timer

FILEPATH = config.dl_root
AUTO_CLEAN_INTERVAL = config.auto_clean_interval

class Cleaner:
    filepath = ''
    autu_clean_interval = ''
    last_auto_clean = 0
    max_timedelta = timedelta(days=1)
    timer = None

    def __init__(self, filepath = FILEPATH, max_timedelta = timedelta(days=1), auto_clean_interval = AUTO_CLEAN_INTERVAL):
        self.last_auto_clean = 0
        self.filepath = filepath
        self.max_timedelta = max_timedelta
        self.autu_clean_interval = auto_clean_interval
        self.timer = Timer(self.autu_clean_interval, self.autocleanOutdated)
        print('清理的文件夹为', filepath)
        
    @staticmethod
    def deleteAllTemp() -> bool:
        error = False
        count = 0
        for (dirpath, dirnames, filenames) in os.walk(FILEPATH):
            for f in filenames:
                try:
                    filepath = os.path.join(dirpath, f)
                    os.unlink(filepath)
                    count += 1
                    print('已删除', f)
                except Exception as err:
                    error = True
                    print(f'删除{f}时出错: ', err)
            print(f'删除了{count}个文件')
        return error

    @staticmethod
    def deleteByName(search_ptn: str):
        ptn = re.compile(search_ptn)
        count = 0

        for (dirpath, dirnames, filenames) in os.walk(FILEPATH):
            for f in filenames:
                if ptn.search(f):
                    try:
                        filepath = os.path.join(dirpath, f)
                        os.unlink(filepath)
                        count += 1
                        print('已删除', f)
                    except Exception as err:
                        print(f'删除{f}时出错: ', err)
            print(f'删除了{count}个文件')

    def deleteByTime(self):
        count = 0
        for (dirpath, dirnames, filenames) in os.walk(FILEPATH):
            for f in filenames:
                try:
                    filepath = os.path.join(dirpath, f)
                    stat = os.stat(filepath)
                    if datetime.now() - self.max_timedelta > datetime.fromtimestamp(stat.st_ctime):
                        os.unlink(filepath)
                        print('已删除', f)
                        count += 1
                except Exception as err:
                    print(f'删除{f}时出错: ', err)
        print(f'删除了{count}个文件')

    def autocleanOutdated(self):
        print('正在执行自动清理')
        try:
            self.deleteByTime()
        except Exception as err:
            print('autocleanOutdated 中途错误: ', err)

    def startAutoClean(self):
        self.timer.start()

    def stopAutoClean(self) -> bool:
        if self.timer.is_alive():
            self.timer.cancel()
            return True
        else:
            return False
