import os
import time
from collections import namedtuple
from yt_dlp import YoutubeDL
import yt_dlp

from .groupList import yellow_book
from .manager import Manager
from .utils import replyFunc

Contact = namedtuple('Contact', [
    'group_id',
    'user_id'
])

MAX_ALLOW_SIZE = 20*1024*1024*1024
BASE_URL = 'https://shelf.a-wsl.com/'

class Task():
    def __init__(self, url: str, contact: Contact, **kwargs):
        self.contact = contact
        self.args = kwargs
        self.url = url
        self.start = kwargs['start']
        self.end = kwargs['end']
        self.avg_down_speed = 0
        self.avg_up_speed = 0
        self.elapsed = 0
        self.title = ''
        self.status = ''
        self.video_id = ''
        self.uploader = ''
        self.filepath = ''
        self.filepath_cut = ''
        self.filename = ''
        self.filename_cut = ''
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.status_text = ''
        self.add_time = time.time() + 8 * 3600
        self.file_link = ''
        self.extractInfo()
        self.remote_folder = Manager.selectRmtFolder(self.contact.group_id)
        self.remote_path = ''
        self.finished = False
        self.__files_to_remove = []

    def extractInfo(self):
        with YoutubeDL() as ydl:
            try:
                info = ydl.extract_info(self.url, download=False, process=False)
                self.video_id = info['id']
                self.title = info['title']
                self.uploader = info['uploader']
                self.is_live = info['is_live']
                self.thumbnail = 'https://i.ytimg.com/vi/{}/maxresdefault.jpg'.format(self.video_id)

                best_video = next(f for f in info['formats'][::-1]
                            if f['vcodec'] != 'none' and f['acodec'] == 'none' and f['video_ext'] == 'mp4')
                if best_video['filesize'] > MAX_ALLOW_SIZE:
                    self.status = 'error'
                    self.status_text = '太大啦'
                self.prepare()

            except Exception as err:
                print(err)
                self.status = 'error'
                self.status_text = '会限？私享？还是直播转码未完成？'
            
    def prepare(self):
        if self.status == 'error':
            self.finishTask()
        
        search_ptn = r'\[{}\].mp4'.format(self.video_id) \
            if not (self.start or self.end) \
            else r'\[{}\]\s\[{}-{}\].mp4'.format(
                self.video_id,
                self.start.replace(':', ',') if self.start else '-',
                self.end.replace(':', ',') if self.end else '-'
            )
        
        existed = Manager.checkExist(search_ptn)
        if existed:
            self.status = 'finished'
            self.status_text = '下过了'
            print(self.contact.group_id, self.video_id, existed, '下过了')
            self.remote_path = existed
            self.finishTask()
        elif self.is_live:
            self.status = 'error'
            self.status_text = '直播还没完不准下'
            print(self.contact.group_id, self.video_id, '直播未结束')
            self.finishTask()
        else:
            self.status = 'ready'
            self.status_text = '等待中'
            print(f'群号{self.contact.group_id}, 添加任务{self.title}')

    def startTask(self):
        text = list(filter(None, [
            '\n' if self.start or self.end is not None else None,
            f'从{self.start}开始' if self.start is not None else None,
            f'到{self.end}结束' if self.end is not None else None,
        ]))
        print(f'群号{self.contact.group_id} 开始下载:{self.title}', ' '.join(text))
        replyFunc(self.contact.group_id,
        '开始下载\n{}{}'.format(self.title, ' '.join(text)), [self.thumbnail])

    def finishTask(self):
        if self.status == 'error':
            replyFunc(self.contact.group_id, '{}\n失败：{}'.format(
                self.title,
                self.status_text),
                [self.thumbnail]
            )
        else:
            try:
                self.retrieveLink()
                replyFunc(self.contact.group_id,
                '{}\n{}'.format(self.title, self.file_link), [self.thumbnail])
            except Exception as err:
                replyFunc(self.contact.group_id,
                '{}\n{}'.format(self.title, '获取链接失败'))
        for f in self.__files_to_remove:
            try:
                if os.path.exists(f):
                    os.unlink(f)
            except Exception as err:
                print('删除合并文件出错', err)

    def retrieveLink(self):
        time.sleep(3)
        link = Manager.retrieveLink(self.remote_path)
        self.file_link = link
