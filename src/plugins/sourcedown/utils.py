import re
import time
import asyncio
import subprocess
from typing import Awaitable

from nonebot import get_bot
from nonebot.adapters.onebot.v11.adapter import Bot, Message, MessageSegment

bot: Bot = False
async def get_bot():
    await asyncio.sleep(3)
    global bot
    bot = get_bot()
asyncio.gather(get_bot())

async def reply(group_id, text = '', imgs = []):
    msg = Message([])
    if len(text) > 0:
        msg.append(MessageSegment.text(text))
    if len(imgs) > 0:
        for img in imgs:
            msg.append(MessageSegment.image(img))

    try:
        await send_group_msg(group_id, msg)
    except:
        await send_group_msg(group_id, Message(text))

async def send_group_msg(group_id, msg: Message):
    print(msg)
    await bot.call_api('send_group_msg', group_id = group_id, message = Message(msg))

def timestamp_proc(ts: str):
    ptn = re.compile(r'\d{2}[:：]\d{2}[:：]\d{2}')
    match = ptn.search(ts)
    if match is None:
        return None
    return match.group(0).replace('：', ':')

def sub_proc_watchdog(proc: subprocess.Popen):
    def _watchdog():
        while True:
            code = proc.poll()
            if code == 0:
                print('子进程完成')
                return
            elif code == None:
                pass
            else:
                proc.terminate()
                raise RuntimeError('出错啦', proc.args)
                break
            time.sleep(1)

    ensure_async(_watchdog)

def ensure_async(func: Awaitable, *args):
    loop: asyncio.AbstractEventLoop = None
    
    in_loop = False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError as err:
        in_loop = True
    loop.run_in_executor(None, func, *args) if loop \
    else asyncio.run(func(*args))
