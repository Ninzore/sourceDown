import re
import asyncio
import shlex
import argparse

from nonebot import on_message, on_regex
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.adapters import Message, MessageSegment
from nonebot.params import Arg, CommandArg, ArgPlainText, Matcher
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP

from .downloadTask import Task, Contact
from .downloader import Downloader
from .manager import Manager
from .utils import timestampProc
from .autoclean import Cleaner

ytb_dl = on_regex('^下载\s?https:\/\/((www|m)\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_\-]{11})', permission=GROUP)
manage = on_regex('^群文件夹链接$', permission=GROUP)
task_status = on_regex('^查看任务进度$', permission=GROUP)
task_cancel = on_regex('^重置当前任务$', permission=GROUP)
del_temp = on_regex('^清理一下缓存$', permission=GROUP)

downloader = Downloader()
ytb_url_ptn = re.compile(r'(https:\/\/((www|m)\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_\-]{11}))')

dl_cmd_parser = argparse.ArgumentParser()
dl_cmd_parser.add_argument('--开始', '-s', dest='start')
dl_cmd_parser.add_argument('--结束', '-to', dest='end')

cleaner = Cleaner()
cleaner.startAutoClean()

@ytb_dl.handle()
async def _(event: GroupMessageEvent):
    await ytb_dl.send('收到')
    text = event.get_plaintext()
    url =  ytb_url_ptn.search(text).group(0)

    cmd = cmdStrHandler(text, dl_cmd_parser)
    start = timestampProc(cmd.start) if cmd.start else None
    end = timestampProc(cmd.end) if cmd.end else None

    if cmd.start and start == None:
        await ytb_dl.finish('开始时间标记错啦！')
    if cmd.end and end == None:
        await ytb_dl.finish('结束时间标记错啦！')

    task = Task(url, Contact(event.group_id, event.user_id), start=start, end=end)
    await task.extractInfo()

    if task.status != 'ready':
        await ytb_dl.finish(task.status_text)
    elif task.is_live:
        await ytb_dl.finish('仍在直播中无法下载')

    asyncio.get_event_loop().run_in_executor(None, downloader.addQueue, task)

@manage.handle()
async def _(event: GroupMessageEvent):
    await manage.send(Manager.retrieveRemoteFolderLink(event.group_id))

@task_status.handle()
async def _(event: GroupMessageEvent):
    if not downloader.current_task:
        await task_status.finish('当前无任务')
    await task_status.send('当前任务: {}\n{}\n{}'.format(downloader.current_task.uploader, downloader.current_task.title, downloader.current_task.status_text))

@task_cancel.handle()
async def _(event: GroupMessageEvent):
    if not downloader.current_task:
        await task_cancel.finish('当前无任务')
    else:
        downloader.current_task.status = 'error'
        downloader.current_task.status_text = '任务被手动取消'
        downloader.current_task.finishTask()
        downloader.current_task = None
        await task_cancel.finish('已经手动取消当前任务')

@del_temp.handle()
async def _(event: GroupMessageEvent):
    errcode = Cleaner.deleteAllTemp()
    if errcode is True:
        await del_temp.finish('已完成清理')
    else:
        await del_temp.finish('清理失败')

def cmdStrHandler(raw: str, parser) -> argparse.Namespace:
    raw_ = raw.split(' ', 1)
    raw_cmd = raw_[1] if len(raw_) > 1 else ''
    cmd_list = shlex.split(raw_cmd)
    args, unknown = parser.parse_known_args(cmd_list)
    return args
