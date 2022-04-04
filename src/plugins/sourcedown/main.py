import re
import asyncio

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

ytb_dl = on_regex('^下载\s?https:\/\/((www|m)\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_\-]{11})', permission=GROUP)
manage = on_regex('^群文件夹链接', permission=GROUP)
task_status = on_regex('^查看任务进度', permission=GROUP)

downloader = Downloader()
ytb_url_ptn = re.compile(r'(https:\/\/((www|m)\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_\-]{11}))')

@ytb_dl.handle()
async def _(event: GroupMessageEvent):
    await ytb_dl.send('收到')
    text = event.get_plaintext()
    url =  ytb_url_ptn.search(text).group(0)
    task = Task(url, Contact(event.group_id, event.user_id))
    if task.is_live:
        await ytb_dl.finish('仍在直播中无法下载')
    asyncio.get_event_loop().run_in_executor(None, downloader.addQueue, task)

@manage.handle()
async def _(event: GroupMessageEvent):
    await manage.send(Manager.retrieveRemoteFolderLink(event.group_id))

@task_status.handle()
async def _(event: GroupMessageEvent):
    if not downloader.current_task:
        await task_status.finish('当期无任务')
    await task_status.send('当前任务: {}\n{}\n{}'.format(downloader.current_task.uploader, downloader.current_task.title, downloader.current_task.status_text))
