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
    "user_id"
])

class Task():
    def __init__(self, url: str, contact: Contact, **kwargs):
        self.contact = contact
        self.args = kwargs
        self.url = url
        self.avg_down_speed = 0
        self.avg_up_speed = 0
        self.elapsed = 0
        self.title = ''
        self.status = ''
        self.video_id = ''
        self.uploader = ''
        self.filepath = ''
        self.filename = ''
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.status_text = ''
        self.add_time = time.time() + 8 * 3600
        self.file_link = ''
        self.extractInfo()
        self.thumbnail = 'https://i.ytimg.com/vi/{}/maxresdefault.jpg'.format(self.video_id)
        self.remote_folder = Manager.selectRmtFolder(self.contact.group_id)
        self.remote_path = ''
        self.finished = False

    def extractInfo(self):
        with YoutubeDL() as ydl:
            info = ydl.extract_info(self.url, download=False, process=False)
            self.video_id = info['id']
            self.title = info['title']
            self.uploader = info['uploader']
            self.is_live = info['is_live']
    
    def finishTask(self):
            self.retrieveLink()

    def retrieveLink(self):
        time.sleep(3)
        link = Manager.retrieveLink(self.remote_path)
        self.file_link = link if link else self.title + '失败'
        replyFunc(self.contact.group_id, '{}\n{}'.format(self.title, self.file_link), [self.thumbnail])
        os.unlink(self.filepath)
