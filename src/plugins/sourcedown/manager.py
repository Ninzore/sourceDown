import os
import re
import subprocess
from pathlib import Path

from .groupList import yellow_book
from . import config

REMOTE_DRV = config.remote_drv
MOUNT_FLD = config.mount_fld

class Manager:
    @staticmethod
    def retrieve_remote_folder_link(group_id):
        remote_path = Manager.select_rmt_folder(group_id)
        return Manager.retrieve_link(remote_path)

    @staticmethod
    def select_rmt_folder(group_id):
        remote_path = yellow_book.get(group_id)
        if not remote_path:
            remote_path = '杂货'
        return REMOTE_DRV + remote_path

    @staticmethod
    async def retrieve_link(remote_path):
        proc = subprocess.run(['rclone', 'link', remote_path], stdout=subprocess.PIPE)
        if proc.returncode == 0:
            return proc.stdout.decode('utf-8')
        return False

    @staticmethod
    def mk_remote_dir(remote_path):
        proc = subprocess.run(['rclone', 'mkdir', '{}{}'.format(REMOTE_DRV, remote_path)])
        if proc.returncode == 0:
            return True
        return False

    @staticmethod
    def check_exist(search_ptn: str):
        ptn = re.compile(search_ptn)
        rootpath = Path(MOUNT_FLD)
        for dirpath, dirnames, filenames in os.walk(MOUNT_FLD):
            for f in filenames:
                if ptn.search(f):
                    # 如果就是根目录
                    if Path(dirpath) == rootpath:
                        return REMOTE_DRV + f
                    else:
                        return REMOTE_DRV + os.path.join(os.path.relpath(dirpath, rootpath), f)
        return False
