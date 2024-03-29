import os
import re
import asyncio
import traceback
import subprocess
import sqlite3
from yt_dlp import YoutubeDL
import yt_dlp

from . import config
from .downloadTask import Task, Contact
from .manager import Manager
from .utils import reply, sub_proc_watchdog
from .error import CanceledTask

db_name = 'queue.db'
pattern = re.compile(r'Transferred')
OUT_PATH = config.dl_root
CONCURRENT_FREG = config.concurrent_fragment_downloads

if not os.path.exists(OUT_PATH):
    os.mkdir(OUT_PATH)


# create table DownloadQueue
# (
#     id       integer not null
#         constraint DownloadQueue_pk
#             primary key autoincrement,
#     title    text    not null,
#     url      text    not null,
#     status   text    not null,
#     group_id integer not null,
#     user_id  integer,
#     add_time TIMESTAMP default CURRENT_TIMESTAMP not null
# );

def init():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    dbOpreate('''CREATE TABLE IF NOT EXISTS DownloadQueue
    (
        id       INTEGER NOT NULL
                 PRIMARY KEY AUTOINCREMENT,
        title    TEXT    NOT NULL,
        url      TEXT    NOT NULL,
        status   TEXT    NOT NULL,
        group_id INTEGER NOT NULL,
        user_id  INTEGER,
        add_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );''')
    
def dbOpreate(sql):
    try:
        db = sqlite3.connect(db_name)
        cur = db.cursor()
        cur.execute(sql)
        db.commit()
    except sqlite3.Error as err:
        print('Sqlite error occured when execute {}:\n{}'.format(sql, err))
    finally:
        if db:
            db.close()

# init()

# class postprocessor_hook(yt_dlp.postprocessor.PostProcessor):
#     def run(self, info):
#         self.to_screen('Doing stuff')
#         return [], info

class Downloader():
    def __init__(self, **kwargs):
        self.args = kwargs
        self.current_task = None
        self.task_queue = []
        self.ydl_opts_normal = {
            'paths': {'home': OUT_PATH},
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'progress_hooks': [self.status_hook],
            'postprocessor_hooks': [self.postprocessor_hook]
        }
        self.ydl_opts_live = {
            'paths': {'home': OUT_PATH},
            'is_from_start': True,
            'concurrent_fragment_downloads': CONCURRENT_FREG,
            'progress_hooks': [self.status_hook],
            'postprocessor_hooks': [self.postprocessor_hook]
        }

    def status_hook(self, d):
        if self.current_task.status == 'canceled':
            raise CanceledTask(self.current_task.status_text)

        if d['status'] == 'downloading':
            speed = d['speed']
            self.current_task.elapsed = d['elapsed']
            self.current_task.downloaded_bytes = d['downloaded_bytes']
            
            if not self.current_task.was_live:
                self.current_task.total_bytes = d['total_bytes']
                self.current_task.speed = speed / 1024 / 1024 if type(speed) is float else 0
                self.current_task.status_text = '当前下载速度：{:.2f}MB/s,\n进度: {:.2f}%'.format(
                    self.current_task.speed,
                    100 * self.current_task.downloaded_bytes / self.current_task.total_bytes)
            else:
                self.current_task.total_bytes = d['total_bytes_estimate']
                self.current_task.speed = speed / 1024 / 1024 if type(speed) is float else 0
                if self.current_task.total_bytes == 0:
                    self.current_task.status_text = '当前下载速度：{:.2f}MB/s,\n进度: {:.2f}%'.format(
                        self.current_task.speed * CONCURRENT_FREG,
                        d['fragment_index'] / d['fragment_count'])
                else:
                    self.current_task.status_text = '当前下载速度：{:.2f}MB/s,\n进度: {:.2f}%'.format(
                        self.current_task.speed,
                        100 * self.current_task.downloaded_bytes / self.current_task.total_bytes)
        elif d['status'] == 'finished':
            print('finish part download')
        else:
            print('download error')
            self.current_task.status_text = '下载错误'

    def postprocessor_hook(self, d):
        """
        merger status has 'started' and 'finished'
        """
        
        if self.current_task is not None and d['status'] == 'started':
            print('下载完成开始合并', self.current_task.contact.group_id, self.current_task.title)
            self.current_task.status_text = '下载完成，正在合并文件'
        
        elif self.current_task is not None and self.current_task.finished is False and d['status'] == 'finished':
            print('文件合并完成', self.current_task.contact.group_id, self.current_task.title)
            self.current_task.status_text = '文件合并完成，等待上传'

            self.current_task.finished = True
            self.current_task.filepath = d['info_dict']['filepath']
            self.current_task.filename = os.path.basename(self.current_task.filepath)
            print(self.current_task.title, 'finished')
            self.current_task.status == "finished"
            if '__files_to_merge' in d['info_dict']:
                self.current_task.__files_to_remove = d['info_dict']['__files_to_merge']

    def add_queue(self, task: Task):
        # dbOpreate('''INSERT INTO DownloadQueue (
        #         title, url, status,
        #         group_id, user_id
        #     )
        #     VALUES (
        #         '{title}', '{url}', '{status}',
        #         '{group_id}', '{user_id}'
        #     )'''.format(title=self.title, url=self.url, status=self.status,
        #     group_id=self.contact.group_id, user_id=self.contact.user_id))
        
        if self.current_task is None and task.status != 'error':
            self.current_task = task
            asyncio.run(self.download())
        elif task.status == 'error':
            asyncio.run(task.finish())
            asyncio.run(self.next_task())
        else:
            self.task_queue.append(task)
            print('{} {} {} 已经添加到队列，前面堆着{}个任务'.format(
                task.contact.group_id,
                task.title,
                task.video_id,
                len(self.task_queue)
            ))
            asyncio.run(reply(task.contact.group_id, '已经添加到队列，前面堆着{}个任务'.format(len(self.task_queue))))

    async def next_task(self):
        if len(self.task_queue) > 0:
            self.current_task = self.task_queue.pop(0)
            if self.current_task.status == 'error':
                await self.current_task.finish()
            else:
                await self.download()
        else:
            self.current_task = None
            print('All tasks done')

    async def download(self):
        self.current_task.status = 'downloading'
        await self.current_task.start_task()
        with YoutubeDL(self.ydl_opts_normal \
        if self.current_task.was_live == False \
        else self.ydl_opts_live) as ydl:
            try:
                ydl.download([self.current_task.url])
            except CanceledTask as err:
                await self.cancel_task('任务被手动取消')
            except Exception as err:
                traceback.print_exc()
                print(f'{self.current_task.contact.group_id} {self.current_task.video_id} 出错: {err}')
                await self.cancel_task('下载失败')
        
        if self.current_task.status != 'error':
            if self.current_task.start or self.current_task.end:
                await self.cut()
            else:
                await self.upload()
        await self.next_task()
    
    async def cut(self):
        print(f'{self.current_task.contact.group_id} {self.current_task.video_id} 二刀流启动中')
        start = self.current_task.start or '-'
        end = self.current_task.end or '-'
        filename = self.current_task.filename
        i = filename.rfind('.')
        
        self.current_task.filename_cut = filename[:i] + ' [{}-{}]'.format(
            start.replace(':', ','), end.replace(':', ',')
        ) + filename[i:]
        self.current_task.filepath_cut = self.current_task.filepath.replace(
            filename, self.current_task.filename_cut)
        self.current_task.status_text = '正在施展二刀流'
        start = self.current_task.start
        end = self.current_task.end

        try:
            proc = subprocess.Popen(
                list(filter(None, [
                    'ffmpeg',
                    '-ss' if start is not None else None, start or None,
                    '-to' if end is not None else None, end or None,
                    '-i', self.current_task.filepath,
                    '-c', 'copy',
                    '-avoid_negative_ts', 'make_non_negative',
                    '-y', '-loglevel', 'warning',
                    self.current_task.filename_cut,
                ])),
                cwd=OUT_PATH,
                stdout=subprocess.PIPE
            )
            print('ffmpeg启动')
            sub_proc_watchdog(proc)

            for line in proc.stdout:
                try:
                    line = line.decode('utf-8')
                except UnicodeDecodeError as err:
                    print(err)
                print(line)
            
            print(f'{self.current_task.contact.group_id} {self.current_task.video_id} 二刀流结束')
            await self.upload()
        except Exception as err:
            print('二刀流失败', err)
            await self.cancel_task('剪辑失败')

    async def upload(self):
        filename = ''
        filepath = ''
        if (len(self.current_task.filename_cut)) > 0:
            filename = self.current_task.filename_cut
            filepath = self.current_task.filepath_cut
        else:
            filename = self.current_task.filename
            filepath = self.current_task.filepath
        
        self.current_task.remote_path = '{}/{}'.format(
            self.current_task.remote_folder, filename)

        
        self.current_task.status_text = '准备上传'

        try:
            proc = subprocess.Popen(
                ['rclone', 'copyto', '-P',
                '--drive-chunk-size', '512M',
                filepath,
                self.current_task.remote_path],
                stdout=subprocess.PIPE)
            
            print(f'{self.current_task.contact.group_id} {self.current_task.video_id} 开始上传:', filename)
            sub_proc_watchdog(proc)
            i = 0
            for line in proc.stdout:
                if self.current_task.status == 'error':
                    raise Exception(self.current_task.status_text)
                elif self.current_task.status == 'canceled':
                    raise CanceledTask(self.current_task.status_text)
                try:
                    line = line.decode('utf-8')
                except UnicodeDecodeError as err:
                    line = '1' + line[err.end:len(line)].decode('utf-8')

                match = pattern.search(line)
                if not match or match.start() == 0:
                    continue

                raw = line[match.end()+5:len(line)-1].replace('\t', "").replace(' ', "")
                groups = raw.split(',')
                text = '上传中: {}, 进度:{}\n速度:{}\n预计结束: {}' \
                .format(groups[0], groups[1], groups[2], groups[3][3:])
                self.current_task.status_text = text

                i = i + 1
                if i > 8:
                    i = 0
                    print(text.replace('\n', ' '))
            
            print(f'{self.current_task.contact.group_id} {self.current_task.video_id} 下载完成')
            await self.current_task.finish()
        
        except CanceledTask as err:
                await self.cancel_task('任务被手动取消')
        except Exception as err:
            print(f'{self.current_task.contact.group_id} {self.current_task.video_id} 上传失败', err)
            await self.cancel_task('上传失败')
    
    async def cancel_task(self, status_text: str):
        self.current_task.status = 'error'
        self.current_task.status_text = status_text
        await self.current_task.finish()
